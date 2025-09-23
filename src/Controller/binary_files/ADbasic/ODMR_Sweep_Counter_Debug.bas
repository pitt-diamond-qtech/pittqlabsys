'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 1000000
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
'   Par_4  = DAC_CH    (1..2)
'   Par_8  = CHUNK_US  (µs, default 200 if 0)
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

'--- working vars ---
Dim n_steps, n_points, k As Long
Dim dac_ch As Long
Dim settle_us, dwell_us As Long
Dim old_cnt, new_cnt, diff As Long
Dim vmin_dig, vmax_dig As Long
Dim step_dig, pos As Long
Dim vmin_clamped, vmax_clamped, t As Float
Dim sum_counts, max_counts, max_idx As Long

'--- state machine vars ---
Dim state As Long
Dim settle_rem_us, dwell_rem_us, tick_us As Long

'--- result buffers (1-based indexing) ---
Dim Data_1[200000]  As Long   ' counts per step
Dim Data_2[200000]  As Long   ' DAC digits per step
Dim FData_1[200000] As Float  ' volts per step
Dim Data_3[200000]  As Long   ' triangle pos per step

Init:
  ' default chunk 200 µs if Par_8 not set yet
  IF (Par_8 <= 0) THEN
    Par_8 = 200
  ENDIF
  Processdelay = Par_8 * 100   ' (10 ns units)

  ' Counter 1: clk/dir, count up on rising edges (DIR tied high)
  Cnt_Enable(0)
  Cnt_Clear(0001b)
  Cnt_Mode(1, 00000000b)   ' bit0=0 clk/dir, no inversions (count up)
  Cnt_SE_Diff(0000b)
  Cnt_Enable(0001b)

  ' Watchdog (debug): 5 s (units = 10 µs) - increased for longer dwell times
  Watchdog_Init(1, 500000, 1111b)

  ' Initialize state machine
  state = 0

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
  Par_25 = Par_25 + 1
  tick_us = Processdelay / 100  ' 10 ns units -> µs

  IF (Par_10 = 0) THEN
    ' idle
    state = 0
    Watchdog_Reset()
  ELSE
    SelectCase state

      ' ------------------------------------------------------
      CASE 0   ' START NEW SWEEP (when Par_20 == 0)
        IF (Par_20 <> 0) THEN
          state = 90
        ELSE
          ' --- snapshot & clamp ---
          n_steps   = Par_1
          IF (n_steps < 2) THEN 
            n_steps = 2 
          ENDIF
          settle_us = Par_2
          dwell_us  = Par_3
          dac_ch    = Par_4
          IF (dac_ch < 1) THEN 
            dac_ch = 1
          ENDIF
          IF (dac_ch > 2) THEN 
            dac_ch = 2 
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

          ' Preload DAC to first code (computed in next state)
          k   = 0
          Par_22 = 0
          Par_23 = 0
          Par_24 = 0.0

          ' Clear summaries
          Par_30 = 0
          Par_31 = -2147483648
          Par_32 = 0
          FPar_33 = 0.0

          state = 20
        ENDIF

      ' ------------------------------------------------------
      CASE 20   ' PREP CURRENT STEP: compute pos, code; output; start settle
        IF (k < n_steps) THEN
          pos = k
        ELSE
          pos = (2 * n_steps) - 2 - k
        ENDIF
        Par_22 = k
        Par_23 = pos

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

        Write_DAC(dac_ch, Data_2[k+1])
        Start_DAC()
        settle_rem_us = settle_us
        dwell_rem_us  = dwell_us
        state = 30

      ' ------------------------------------------------------
      CASE 30   ' SETTLE (excluded from counting)
        IF (settle_rem_us > 0) THEN
          IF (settle_rem_us > tick_us) THEN
            settle_rem_us = settle_rem_us - tick_us
          ELSE
            settle_rem_us = 0
          ENDIF
          Watchdog_Reset()
        ELSE
          state = 40
        ENDIF

      ' ------------------------------------------------------
      CASE 40   ' LATCH BASELINE
        Cnt_Latch(0001b)
        old_cnt = Cnt_Read_Latch(1)
        state = 50

      ' ------------------------------------------------------
      CASE 50   ' DWELL (counting window)
        IF (dwell_rem_us > 0) THEN
          IF (dwell_rem_us > tick_us) THEN
            dwell_rem_us = dwell_rem_us - tick_us
          ELSE
            dwell_rem_us = 0
          ENDIF
          Watchdog_Reset()
        ELSE
          state = 60
        ENDIF

      ' ------------------------------------------------------
      CASE 60   ' LATCH END, store delta
        Cnt_Latch(0001b)
        new_cnt = Cnt_Read_Latch(1)
        diff = new_cnt - old_cnt
        IF (diff < 0) THEN
          diff = -diff
        ENDIF   ' magnitude; drop this if you want signed
        Data_1[k+1] = diff
        Par_30 = Par_30 + diff
        IF (diff > Par_31) THEN
          Par_31 = diff
          Par_32 = k
        ENDIF
        state = 70

      ' ------------------------------------------------------
      CASE 70   ' ADVANCE STEP
        k = k + 1
        IF (k >= n_points) THEN
          ' Finish sweep
          IF (n_points > 0) THEN
            FPar_33 = Par_30 / n_points
          ELSE
            FPar_33 = 0.0
          ENDIF
          Par_20 = 1              ' READY
          state  = 90             ' wait for PC
        ELSE
          state = 20              ' next step
        ENDIF

      ' ------------------------------------------------------
      CASE 90   ' WAIT FOR PC
        IF (Par_20 = 0) THEN
          state = 0
        ELSE
          Watchdog_Reset()
        ENDIF

      CaseElse
        state = 0
    EndSelect
  ENDIF

End  ' <-- single End that closes the Event section

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
  ELSEIF (Par_4 > 2) THEN
    dac_ch = 2
  ELSE
    dac_ch = Par_4
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

End