'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 300000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = Low
' Priority_Low_Level             = 1
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Duttlab
'<Header End>
'
' ODMR Sweep Counter Script — MULTI-WAVEFORM (state machine, chunked processing)
' Multiple waveforms on DACx; counts falling edges on Counter 1.
' Non-blocking handshake: Par_20=1 when ready; PC must clear to 0.
' State machine prevents Get_Par timeouts by doing small chunks per Event.
' Supports: Triangle, Ramp, Sine, Square, Noise, Custom table waveforms.

#Include ADwinGoldII.inc

'================= Interface =================
' From Python:
'   FPar_1 = Vmin [V] (clamped to [-1,+1])
'   FPar_2 = Vmax [V] (clamped to [-1,+1])
'   FPar_5 = Square setpoint [V] (optional, for Par_7=3)
'   Par_1  = N_STEPS   (>=2)
'   Par_2  = SETTLE_US (µs)
'   Par_3  = DWELL_US  (µs)
'   Par_4  = EDGE_MODE  (0=rising, 1=falling)
'   Par_5  = DAC_CH    (1..2)
'   Par_6  = DIR_SENSE (0=DIR Low=up, 1=DIR High=up)
'   Par_7  = WAVEFORM  (0=Triangle, 1=Ramp, 2=Sine, 3=Square, 4=Noise, 100=Custom)
'   Par_8  = PROCESSDELAY_US (µs, 0=auto-calculate from dwell time)
'   Par_9  = OVERHEAD_FACTOR (1.0=no correction, 1.2=20% overhead, default=1.2)
'   Par_10 = START     (1=run, 0=idle)
'   Par_11 = RNG_SEED  (random number generator seed, default=12345)
' To Python:
'   Data_1[]  = counts per step (LONG)
'   Data_2[]  = DAC digits per step (LONG)
'   Data_3[]  = custom waveform table (LONG, for Par_7=100)
'   Par_20    = ready flag (1=data ready)
'   Par_21    = number of points (varies by waveform)
'   Par_25    = heartbeat
'   Par_26    = current state (255=idle, 10=prep, 30=settle, etc.)
'   Par_71    = Processdelay (ticks)
'   Par_80    = signature (7777)
'   Par_81    = waveform type used (0-4, 100)
'   Par_82    = actual n_points for this waveform
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
Dim dac_ch, edge_mode, dir_sense As Long
Dim settle_us, dwell_us As Long
Dim old_cnt, new_cnt As Long
Dim fd As Float
Dim vmin_dig, vmax_dig As Long
Dim step_dig, pos As Long
Dim vmin_clamped, vmax_clamped, t As Float

'--- waveform vars ---
Dim waveform_type As Long
Dim square_setpoint As Float
Dim square_dig As Long
Dim rng_state As Long
Dim u, v, vmid, vamp As Float

'--- state machine vars ---
Dim state As Long
Dim settle_rem_us, dwell_rem_us, tick_us As Long
Dim overhead_factor As Float
Dim hb_div As Long ' heartbeat prescaler to avoid spamming
' Processdelay control: hybrid approach (inline calculation)
Dim pd_us, pd_ticks As Long
  
'--- result buffers (1-based indexing) ---
Dim Data_1[1000]  As Long   ' counts per step
Dim Data_2[1000]  As Long   ' DAC digits per step
Dim Data_3[1000]  As Long   ' custom waveform table (for Par_7=100)

Init:
  
  ' Par_8 > 0: Python specified (µs) -> convert to ticks
  ' Par_8 = 0: Auto-calculate based on dwell time for optimal chunking
  IF (Par_8 > 0) THEN
    pd_us = Par_8   ' Python specified (µs)
  ELSE
    ' Auto-calculate: aim for ~10 chunks per dwell
    pd_us = Par_3 / 10   ' dwell_us / 10
  ENDIF
  
  ' Convert µs to ticks (approximate: 1µs ≈ 300 ticks)
  pd_ticks = pd_us * 300
  
  ' Clamp to reasonable bounds
  IF (pd_ticks < 1000) THEN pd_ticks = 1000      ' min 3.3µs
  IF (pd_ticks > 5000000) THEN pd_ticks = 5000000 ' max 16.7ms
  IF (pd_ticks <= 0) THEN pd_ticks = 300000      ' safety fallback
  
  
  ' Set Processdelay directly in Init
  Processdelay = pd_ticks
  Par_71 = Processdelay
  
  ' Calculate tick_us once (constant for this session)
  ' Use Par_9 as overhead correction factor (scaled by 10: 10=1.0, 12=1.2, 20=2.0)
  overhead_factor = Par_9 / 10.0  ' Convert scaled integer back to float
  IF (overhead_factor <= 0.0) THEN overhead_factor = 1.2  ' Default to 1.2x for production
  ' Calculate base tick_us, then apply overhead correction
  tick_us = Round(Processdelay * 3.3 / 1000.0 * overhead_factor)   ' Apply overhead correction
  IF (tick_us <= 0) THEN
    tick_us = 1                  ' never allow zero tick
  ENDIF

  ' Validate and clamp parameters once
  n_steps = Par_1
  IF (n_steps < 2) THEN n_steps = 2
  
  settle_us = Par_2
  dwell_us = Par_3
  edge_mode = Par_4
  dac_ch = Par_5
  dir_sense = Par_6
  waveform_type = Par_7
  
  ' Clamp DAC channel
  IF (dac_ch < 1) THEN dac_ch = 1
  IF (dac_ch > 2) THEN dac_ch = 2
  
  ' Clamp voltage range
  vmin_clamped = Clamp(FPar_1, -1.0, 1.0)
  vmax_clamped = Clamp(FPar_2, -1.0, 1.0)
  IF (vmin_clamped > vmax_clamped) THEN
    t = vmin_clamped
    vmin_clamped = vmax_clamped
    vmax_clamped = t
  ENDIF
  
  ' Convert to DAC digits
  vmin_dig = VoltsToDigits(vmin_clamped)
  vmax_dig = VoltsToDigits(vmax_clamped)
  IF (vmin_dig = vmax_dig) THEN n_steps = 2
  
  ' Decide n_points by waveform mode (do this once when you start a sweep)
  SelectCase waveform_type
    Case 0  ' Triangle
      n_points = (2 * n_steps) - 2
    Case 1  ' Ramp/Saw
      n_points = n_steps
    Case 2  ' Sine
      n_points = n_steps
    Case 3  ' Square (constant)
      n_points = n_steps
    Case 4  ' Noise
      n_points = n_steps
    Case 100 ' Custom table
      n_points = n_steps  ' Will be overridden by custom table size
    Case Else
      n_points = (2 * n_steps) - 2  ' default triangle
  EndSelect
  IF (n_points < 2) THEN n_points = 2
  IF (n_points > 1000) THEN n_points = 1000   ' prevent array overflow

  ' Initialize waveform-specific parameters
  square_setpoint = Clamp(FPar_5, -1.0, 1.0)
  square_dig = VoltsToDigits(square_setpoint)
  
  ' Initialize RNG state (use Par_11 as seed if provided, otherwise use default)
  rng_state = Par_11
  IF (rng_state <= 0) THEN rng_state = 12345  ' Default seed

  ' Counter 1: clk/dir, single-ended mode (basic setup)
  Cnt_SE_Diff(0000b)

  ' Watchdog (debug): 5 s (units = 10 µs) - increased for longer dwell times
  Watchdog_Init(1, 500000, 1111b)

  ' Initialize state machine
  state = 255
  hb_div = 0

  Par_20 = 0
  Par_21 = n_points
  Par_25 = 0
  Par_80 = 7777     ' Signature to confirm script is loaded
  Par_81 = waveform_type  ' Report waveform type used
  Par_82 = n_points      ' Report actual n_points
  old_cnt = 0

Event:
  ' ---- heartbeat ----
  hb_div = hb_div + 1
  IF (hb_div >= 10) THEN         ' update heartbeat every ~10 ticks
    Par_25 = Par_25 + 1
    hb_div = 0
  ENDIF

  Par_26 = state                 ' live: which CASE we are in
  Watchdog_Reset()  ' Reset watchdog in Event

  ' ---- async stop: force state = 255 if Par_10 = 0 ----
  IF (Par_10 = 0) THEN
    state = 255
  ENDIF

  ' ---- run state machine unconditionally ----
  Par_26 = state   ' Debug: current state
  SelectCase state

      Case 255     ' IDLE: async start detection and housekeeping
        Rem breathe and advertise that we are alive
        IO_Sleep(1000)   ' 10 µs yield
        Watchdog_Reset()   ' Reset watchdog in idle state
        Par_26 = state
        ' Check for async start: Par_10 flipped to 1
        IF (Par_10 = 1) THEN
          state = 10   ' Start new sweep
        ENDIF

      
      Case 0
        Rem unused - kept for future compatibility
        Par_26 = state
        state = 10
      Case 10     ' SNAPSHOT & PREP: initialize sweep variables
        ' Reset sweep variables for new sweep
        k = 0
        Par_26 = state
        
        ' Configure counter once for entire sweep
        Cnt_Enable(0)
        Cnt_Clear(0001b)
        edge_mode = Par_4  ' 0=rising, 1=falling
        IF (edge_mode = 0) THEN
          ' Rising edges
          IF (Par_6 = 1) THEN
            Cnt_Mode(1, 00000000b)   ' DIR high = count up
          ELSE
            Cnt_Mode(1, 00001000b)   ' invert DIR: DIR low = count up
          ENDIF
        ELSE
          ' Falling edges
          IF (Par_6 = 1) THEN
            Cnt_Mode(1, 00000100b)   ' invert CLK, DIR high = count up
          ELSE
            Cnt_Mode(1, 00001100b)   ' invert CLK and DIR: DIR low = count up
          ENDIF
        ENDIF
        
        state = 20
        

      Case 20     ' PREPARE STEP (counter already configured)
        Par_26 = state
        ' Counter configuration moved to Case 10 (once per sweep)
        state = 30
        

      Case 30     ' ISSUE STEP, START SETTLE
        Par_26 = state
        
        ' Compute step fraction u in [0..1]
        IF (waveform_type = 0) THEN
          ' triangle index (0..N-1..1)
          IF (k < n_steps) THEN
            pos = k
          ELSE
            pos = (2 * n_steps) - 2 - k
          ENDIF
          u = pos / (n_steps - 1.0)
        ELSE
          ' simple forward index
          u = k / (n_points - 1.0)
        ENDIF

        ' Map u -> voltage by mode
        vmid = 0.5 * (vmin_clamped + vmax_clamped)
        vamp = 0.5 * (vmax_clamped - vmin_clamped)

        SelectCase waveform_type
          Case 0 ' Triangle
            v = vmin_clamped + (vmax_clamped - vmin_clamped) * u
          Case 1 ' Ramp/Saw
            v = vmin_clamped + (vmax_clamped - vmin_clamped) * u
          Case 2 ' Sine (one period, start at Vmin)
            ' Use built-in Sin function with proper phase shift
            v = vmid + vamp * Sin(6.2831853 * u - 1.5707963)  ' shift so u=0 near Vmin
            ' Fallback: portable version using half-wave triangle-to-sine approx:
            ' v = vmid + vamp * (1.27323954 * (2*u - 1) - 0.405284735 * (2*u - 1) * Abs(2*u - 1))
          Case 3 ' Square (constant)
            ' use Vmid or FPar_5 if provided
            IF (FPar_5 <> 0.0) THEN
              v = FPar_5
            ELSE
              v = vmid
            ENDIF
          Case 4 ' Noise (uniform in [Vmin, Vmax])
            ' simple LCG: X = (a*X + c) mod 2^31
            rng_state = (1103515245 * rng_state + 12345) AND &H7FFFFFFF
            v = vmin_clamped + ( (rng_state / 2147483647.0) * (vmax_clamped - vmin_clamped) )
          Case 100 ' Custom (use Data_3 buffer)
            ' v will be pulled from user-supplied array
            IF (k < 1000) THEN  ' Safety check
              v = DigitsToVolts(Data_3[k+1])  ' Convert DAC digits back to volts
            ELSE
              v = vmin_clamped  ' Fallback to min
            ENDIF
          Case Else
            v = vmin_clamped + (vmax_clamped - vmin_clamped) * u
        EndSelect

        ' clamp just in case
        IF (v < -1.0) THEN v = -1.0 ENDIF
        IF (v >  1.0) THEN v =  1.0 ENDIF

        ' Convert to DAC digits and store
        Data_2[k+1] = VoltsToDigits(v)

        ' Output DAC and start settle
        Write_DAC(dac_ch, Data_2[k+1])
        Start_DAC()
        
        settle_rem_us = Par_2
        state = 31

      Case 31     ' SETTLE (time-sliced)
        Watchdog_Reset()   ' Reset watchdog during long settle
        Par_26 = state
        IF (settle_rem_us > tick_us) THEN
          settle_rem_us = settle_rem_us - tick_us
          state = 31
        ELSE
          state = 32
        ENDIF

      Case 32     ' OPEN DWELL WINDOW (start fresh)
        ' Start a fresh window: clear -> enable -> dwell
        Cnt_Enable(0)
        Cnt_Clear(0001b)
        Cnt_Enable(0001b)
        
        ' If you want, you can latch once to prove it's zero:
        ' Cnt_Latch(0001b) : old_cnt = Cnt_Read_Latch(1)  ' should be 0
        ' But we simply treat baseline as 0:
        old_cnt = 0
        Par_26 = state
        dwell_rem_us = Par_3
        state = 33

      Case 33     ' DWELL (time-sliced)
        Watchdog_Reset()   ' Reset watchdog during long dwell
        Par_26 = state
        IF (dwell_rem_us >= tick_us) THEN
          dwell_rem_us = dwell_rem_us - tick_us
          state = 33
        ELSE
          state = 34
        ENDIF

      Case 34     ' CLOSE WINDOW, READ, STORE
        Cnt_Latch(0001b)
        new_cnt = Cnt_Read_Latch(1)
        Cnt_Enable(0)        ' Disable counter after dwell window
        Par_26 = state
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
        state = 35

      Case 35     ' NEXT STEP OR FINISH
        k = k + 1
        Par_26 = state
        IF (k >= n_points) THEN
          state = 70
        ELSE
          state = 30
        ENDIF

      Case 70     ' READY HANDSHAKE (non-blocking)
        Par_20 = 1
        IO_Sleep(1000)            ' ~10 µs bus yield
        Watchdog_Reset()
        Par_26 = state
        IF (Par_10 = 0) THEN 
          state = 255
        ELSE 
          IF (Par_20 = 0) THEN 
            state = 10              ' host cleared READY -> next sweep
          ELSE 
            state = 70
          ENDIF
        ENDIF

      CaseElse
        Par_26 = 0
        state = 255

    EndSelect



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
  ' De-arm watchdog so nothing can fire after process stops
  ' if 0 is not allowed as timeout on system, use 1 instead
  Watchdog_Init(1,0,0000b)

  Exit
