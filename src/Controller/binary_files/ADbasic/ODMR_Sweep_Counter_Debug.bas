'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 3000000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = Normal
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Duttlab
'<Header End>
'
' ODMR Sweep Counter Script — DEBUG (state machine, chunked processing)
' Triangle on DACx; counts falling edges on Counter 1.
' Non-blocking handshake: Par_20=1 when ready; PC must clear to 0.
' State machine prevents Get_Par timeouts by doing small chunks per Event.

#Include ADwinGoldII.inc

'================= Interface =================
' From Python:
'   FPar_1 = Vmin [V] (clamped to [-1,+1])
'   FPar_2 = Vmax [V] (clamped to [-1,+1])
'   Par_1  = N_STEPS   (>=2)
'   Par_2  = SETTLE_US (µs)
'   Par_3  = DWELL_US  (µs)
'   Par_4  = EDGE_MODE  (0=rising, 1=falling)
'   Par_5  = DAC_CH    (1..2)
'   Par_6  = DIR_SENSE (0=DIR Low=up, 1=DIR High=up)
'   Par_8  = PROCESSDELAY_US (µs, 0=auto-calculate from dwell time)
'   Par_10 = START     (1=run, 0=idle)
' To Python:
'   Data_1[]  = counts per step (LONG)
'   Data_2[]  = DAC digits per step (LONG)
'   FData_1[] = volts per step (FLOAT)
'   Data_3[]  = triangle pos per step (LONG)
'   Par_20    = ready flag (1=data ready)
'   Par_21    = number of points (2*N_STEPS-2)
'   Par_22    = current step index (0-based)
'   Par_23    = current triangle position
'   Par_24    = current volts (FLOAT)
'   Par_25    = heartbeat
'   Par_30    = total counts (sum)
'   Par_31    = max counts (per step)
'   Par_32    = index of max (0-based)
'   FPar_33   = average counts (float)
'=============================================

'--- helpers (typed return OK; no typed args) ---
Function VoltsToDigits(v) As Long
  VoltsToDigits = Round((v + 10.0) * 65535.0 / 20.0)
EndFunction

Function DigitsToVolts(d) As Float
  DigitsToVolts = (d * 20.0 / 65535.0) - 10.0
EndFunction

' clamp to [lo, hi]
Function Clamp(v, lo, hi) As Float
  IF (v < lo) THEN
    v = lo
  ENDIF
  IF (v > hi) THEN
    v = hi
  ENDIF
  Clamp = v
EndFunction

Sub SetProcessdelay()
  Dim pd_us, pd_ticks As Long
  
  ' Processdelay control: hybrid approach
  ' Par_8 > 0: Python specified (µs) -> convert to ticks
  ' Par_8 = 0: Auto-calculate based on dwell time for optimal chunking
  IF (Par_8 > 0) THEN
    pd_us = Par_8   ' Python specified (µs)
  ELSE
    ' Auto-calculate: aim for ~10 chunks per dwell
    ' This ensures good timing resolution without too many Event calls
    pd_us = Par_3 / 10   ' dwell_us / 10
  ENDIF
  
  ' Convert µs to ticks (approximate: 1µs ≈ 300 ticks)
  pd_ticks = pd_us * 300
  
  ' Clamp to reasonable bounds
  IF (pd_ticks < 1000) THEN pd_ticks = 1000 ENDIF     ' min 3.3µs
  IF (pd_ticks > 5000000) THEN pd_ticks = 5000000 ENDIF ' max 16.7ms
  
  Processdelay = pd_ticks
EndSub

'--- working vars ---
Dim n_steps, n_points, k As Long
Dim dac_ch, edge_mode, dir_sense As Long
Dim settle_us, dwell_us As Long
Dim old_cnt, new_cnt As Long
Dim fd As Float
Dim vmin_dig, vmax_dig As Long
Dim step_dig, pos As Long
Dim vmin_clamped, vmax_clamped, t As Float
Dim sum_counts, max_counts, max_idx As Long

'--- state machine vars ---
Dim state As Long
Dim settle_rem_us, dwell_rem_us, tick_us As Long
Dim hb_div As Long ' heartbeat prescaler to avoid spamming

'--- result buffers (1-based indexing) ---
Dim Data_1[200000]  As Long   ' counts per step
Dim Data_2[200000]  As Long   ' DAC digits per step
Dim FData_1[200000] As Float  ' volts per step
Dim Data_3[200000]  As Long   ' triangle pos per step

Init:
  ' Set optimal Processdelay using hybrid approach
  Call SetProcessdelay()

  ' Counter 1: clk/dir, single-ended mode
  Cnt_Enable(0)
  Cnt_Clear(0001b)
  Cnt_SE_Diff(0000b)
  Cnt_Enable(0001b)

  ' Watchdog (debug): 5 s (units = 10 µs) - increased for longer dwell times
  Watchdog_Init(1, 500000, 1111b)

  ' Initialize state machine
  state = 0
  hb_div = 0

  Par_20 = 0
  Par_21 = 0
  Par_22 = 0
  Par_23 = 0
  Par_24 = 0.0
  Par_25 = 0
  Par_30 = 0
  Par_31 = 0
  Par_32 = 0
  FPar_33 = 0.0
  old_cnt = 0

Event:
  ' ---- heartbeat & tick ----
  hb_div = hb_div + 1
  IF (hb_div >= 10) THEN         ' update heartbeat every ~10 ticks
    Par_25 = Par_25 + 1
    hb_div = 0
  ENDIF

  tick_us = Processdelay * 3.3 / 1000   ' Convert ticks to µs
  IF (tick_us <= 0) THEN
    tick_us = 1                  ' never allow zero tick
  ENDIF

  Par_26 = state                 ' live: which CASE we are in

  ' ---- idle gate ----
  IF (Par_10 = 0) THEN
    state = 0
  ELSE

    SelectCase state

      Case 0        ' START SWEEP (only when Par_20 == 0)
        IF (Par_20 <> 0) THEN
          state = 90
        ELSE
          ' snapshot basic params
          n_steps   = Par_1
          IF (n_steps < 2) THEN
            n_steps = 2
          ENDIF
          settle_us = Par_2
          dwell_us  = Par_3
          edge_mode = Par_4
          dac_ch    = Par_5
          dir_sense = Par_6

          ' clamp DAC ch (nested IF, no ELSEIF)
          IF (dac_ch < 1) THEN
            dac_ch = 1
          ELSE
            IF (dac_ch > 2) THEN
              dac_ch = 2
            ENDIF
          ENDIF

          vmin_clamped = Clamp(FPar_1, -1.0, 1.0)
          vmax_clamped = Clamp(FPar_2, -1.0, 1.0)
          IF (vmin_clamped > vmax_clamped) THEN
            t = vmin_clamped
            vmin_clamped = vmax_clamped
            vmax_clamped = t
          ENDIF

          vmin_dig = VoltsToDigits(vmin_clamped)
          vmax_dig = VoltsToDigits(vmax_clamped)
          IF (vmin_dig = vmax_dig) THEN
            n_steps = 2
          ENDIF

          n_points = (2 * n_steps) - 2
          IF (n_points < 2) THEN
            n_points = 2
          ENDIF
          Par_21 = n_points

          k = 0
          Par_22 = 0
          Par_23 = 0
          Par_24 = 0.0

          ' clear summaries
          Par_30 = 0
          Par_31 = -2147483648
          Par_32 = 0
          FPar_33 = 0.0

          state = 20
        ENDIF

      Case 20     ' PREP STEP: compute DAC code; start settle window
        ' triangle index
        IF (k < n_steps) THEN
          pos = k
        ELSE
          pos = (2 * n_steps) - 2 - k
        ENDIF
        Par_22 = k
        Par_23 = pos

        ' code for this step
        IF (n_steps > 1) THEN
          step_dig = ((vmax_dig - vmin_dig) * pos) / (n_steps - 1)
        ELSE
          step_dig = 0
        ENDIF
        Data_2[k+1] = vmin_dig + step_dig
        
        ' bounds check for DAC digits (should be 0-65535)
        IF (Data_2[k+1] < 0) THEN
          Data_2[k+1] = 0
        ENDIF
        IF (Data_2[k+1] > 65535) THEN
          Data_2[k+1] = 65535
        ENDIF
        
        FData_1[k+1] = DigitsToVolts(Data_2[k+1])
        Data_3[k+1]  = pos
        Par_24 = FData_1[k+1]  ' debug volts

        ' output
        Write_DAC(dac_ch, Data_2[k+1])
        Start_DAC()

        ' configure counter mode for this measurement
        Cnt_Enable(0)
        Cnt_Clear(0001b)
        IF (edge_mode = 0) THEN
          Rem rising edges
          IF (dir_sense = 1) THEN
            Cnt_Mode(1, 00000000b)
          ELSE
            Cnt_Mode(1, 00001000b)
          ENDIF
        ELSE
          Rem falling edges
          IF (dir_sense = 1) THEN
            Cnt_Mode(1, 00000100b)
          ELSE
            Cnt_Mode(1, 00001100b)
          ENDIF
        ENDIF
        Cnt_Enable(0001b)

        ' initialize timers
        settle_rem_us = settle_us
        dwell_rem_us  = dwell_us
        state = 30

      Case 30     ' SETTLE (excluded from counting)
        IF (settle_rem_us > 0) THEN
          IF (settle_rem_us > tick_us) THEN
            settle_rem_us = settle_rem_us - tick_us
          ELSE
            settle_rem_us = 0
          ENDIF
        ELSE
          state = 40
        ENDIF

      Case 40     ' LATCH BASELINE
        Cnt_Latch(0001b)
        old_cnt = Cnt_Read_Latch(1)
        state = 50

      Case 50     ' DWELL (counting window)
        IF (dwell_rem_us > 0) THEN
          IF (dwell_rem_us > tick_us) THEN
            dwell_rem_us = dwell_rem_us - tick_us
          ELSE
            dwell_rem_us = 0
          ENDIF
        ELSE
          state = 60
        ENDIF

      Case 60     ' LATCH END + STORE DELTA
        Cnt_Latch(0001b)
        new_cnt = Cnt_Read_Latch(1)
        
        Rem ---- compute delta with wrap handling using Float arithmetic ----
        fd = new_cnt - old_cnt
        
        IF (fd < 0.0) THEN    
          Rem hardware is unsigned 32-bit     
          Rem modulo 2^32 into [0,2^32)      
          fd = fd + 4294967296.0
        ENDIF

        Rem Direction-agnostic: pick the smaller arc on the 32-bit ring
        IF (fd > 2147483647.0) THEN 
          Rem > 2^31
          fd = 4294967296.0 - fd     
          Rem take the other way around
        ENDIF
        
        Data_1[k+1] = Round(fd)

        Par_30 = Par_30 + Round(fd)
        IF (Round(fd) > Par_31) THEN
          Par_31 = Round(fd)
          Par_32 = k
        ENDIF

        state = 70

      Case 70     ' ADVANCE
        k = k + 1
        IF (k >= n_points) THEN
          IF (n_points > 0) THEN
            FPar_33 = Par_30 / n_points
          ELSE
            FPar_33 = 0.0
          ENDIF
          Par_20 = 1     ' ready
          state  = 90
        ELSE
          state = 20
        ENDIF

      Case 90     ' WAIT FOR PC
        ' no sleeps; just yield this tick
        ' allow PC to clear Par_20
        IF (Par_20 = 0) THEN
          state = 0
        ENDIF

      CaseElse
        state = 0

    EndSelect
  ENDIF

End

Finish:
  ' Mark stopped and clear handshake
  Par_10 = 0
  Par_20 = 0

  ' Disable counter(s) and clear counter 1
  Cnt_Enable(0)
  Cnt_Clear(0001b)

  ' Park DAC channel at 0 V (center)
  IF (Par_4 < 1) THEN
    dac_ch = 1
  ELSE
    IF (Par_4 > 2) THEN
      dac_ch = 2
    ELSE
      dac_ch = Par_4
    ENDIF
  ENDIF
  Write_DAC(dac_ch, VoltsToDigits(0.0))
  Start_DAC()

  ' Reset internal state (optional but tidy)
  state = 0
  k = 0
  Par_21 = 0
  Par_22 = 0
  Par_23 = 0
  Par_24 = 0.0

  Exit