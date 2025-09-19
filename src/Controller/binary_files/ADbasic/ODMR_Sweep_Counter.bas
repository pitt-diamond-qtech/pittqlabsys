'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 1000000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Duttlab
'<Header End>
'
' ODMR Sweep Counter Script for Enhanced ODMR Experiments
' Generates a triangle on DACx (default DAC1) and counts falling edges on Counter 1.
' Non-blocking handshake: PC clears Par_20 to release next sweep.
'
#Include ADwinGoldII.inc

' ===================== Exposed interface =====================
' From Python:
'   FPar_1 = Vmin [V]   (clamped to [-1, +1])
'   FPar_2 = Vmax [V]   (clamped to [-1, +1])
'   Par_1  = N_STEPS    (>=2)
'   Par_2  = SETTLE_US  (us)
'   Par_3  = DWELL_US   (us)
'   Par_4  = DAC_CH     (1..2)
'   Par_10 = START      (1=run, 0=idle)
' To Python:
'   Data_1[] = counts per step (LONG)
'   Data_2[] = DAC digits per step (LONG)
'   Par_20   = 1 when sweep done (PC must clear to 0 to allow next sweep)
'   Par_21   = number of points in last sweep (2*N_STEPS-2)
'   Par_25   = heartbeat counter (increments every Event tick)
' ============================================================

' ---- helpers (typed return OK; no typed args) ----
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

' ---- working vars ----
Dim n_steps, n_points, k      As Long
Dim dac_ch                    As Long
Dim settle_us, dwell_us       As Long
Dim last_cnt, cur_cnt         As Long
Dim vmin_dig, vmax_dig        As Long
Dim step_dig, pos             As Long
Dim fd                        As Float
Dim vmin_clamped, vmax_clamped, t As Float

' ---- result buffers (1-based indexing) ----
Dim Data_1[100000] As Long     ' counts per step
Dim Data_2[100000] As Long     ' DAC digits per step

Init:
  ' Event timing isn’t critical; waits use IO_Sleep (10 ns units)
  Processdelay = 10000

  ' Counter 1: clock/direction, invert A/CLK => falling edges
  Cnt_Enable(0)
  Cnt_Clear(0001b)
  Cnt_Mode(1, 00000100b)   ' bit0=0 clk/dir, bit2=1 invert A/CLK
  Cnt_SE_Diff(0000b)       ' single-ended
  Cnt_Enable(0001b)

  ' Watchdog (debug-friendly: 1 s). Keep Reset calls in code.
  Watchdog_Init(1, 100000, 1111b)   ' time units = 10 µs

  ' Handshake init
  Par_20 = 0
  Par_21 = 0
  Par_25 = 0
  last_cnt = 0

Event:
  ' Heartbeat so the PC can see Event is running
  Par_25 = Par_25 + 1

  ' If STOP, just idle this tick
  IF (Par_10 = 0) THEN
    IO_Sleep(1000)          ' ~10 µs
    Watchdog_Reset()
  ELSE

    ' If previous sweep not yet fetched, idle (non-blocking handshake)
    IF (Par_20 <> 0) THEN
      IO_Sleep(1000)
      Watchdog_Reset()

    ELSE
      ' ----------- run ONE triangle sweep -----------

      ' 1) Snapshot params
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

      ' 2) Clamp & order V range to [-1, +1]
      vmin_clamped = Clamp(FPar_1, -1.0, 1.0)
      vmax_clamped = Clamp(FPar_2, -1.0, 1.0)
      IF (vmin_clamped > vmax_clamped) THEN
        t = vmin_clamped
        vmin_clamped = vmax_clamped
        vmax_clamped = t
      ENDIF

      ' 3) Convert to digits
      vmin_dig = VoltsToDigits(vmin_clamped)
      vmax_dig = VoltsToDigits(vmax_clamped)
      IF (vmin_dig = vmax_dig) THEN 
        n_steps = 2 
      ENDIF

      ' 4) Point count and preload DAC
      n_points = (2 * n_steps) - 2
      IF (n_points < 2) THEN 
        n_points = 2 
      ENDIF
      Par_21 = n_points

      Write_DAC(dac_ch, vmin_dig)
      Start_DAC()

      ' Base the incremental counter window
      Cnt_Latch(0001b)
      last_cnt = Cnt_Read_Latch(1)

      ' 5) Sweep
      For k = 0 To (n_points - 1)

        ' position along triangle 0..n_steps-1..1
        IF (k < n_steps) THEN
          pos = k
        ELSE
          pos = (2 * n_steps) - 2 - k
        ENDIF

        ' digits at this step
        IF (n_steps > 1) THEN
          step_dig = ((vmax_dig - vmin_dig) * pos) / (n_steps - 1)
        ELSE
          step_dig = 0
        ENDIF
        Data_2[k+1] = vmin_dig + step_dig

        ' output
        Write_DAC(dac_ch, Data_2[k+1])
        Start_DAC()

        ' settle
        IF (settle_us > 0) THEN
          IO_Sleep(settle_us * 100)    ' 1 µs = 100 * 10 ns
        ENDIF

        ' dwell
        IF (dwell_us > 0) THEN
          IO_Sleep(dwell_us * 100)
        ENDIF

        ' latch & read; wrap-safe delta
        Cnt_Latch(0001b)
        cur_cnt = Cnt_Read_Latch(1)

        fd = cur_cnt - last_cnt
        IF (fd < 0.0) THEN
          fd = fd + 4294967296.0       ' add 2^32 in float space
        ENDIF
        Data_1[k+1] = Round(fd)
        last_cnt = cur_cnt

        Watchdog_Reset()
      Next k

      ' 6) Signal ready — NON-BLOCKING (do not wait here)
      Par_20 = 1

      ' Return from Event; PC will clear Par_20 when done
    ENDIF

  ENDIF
  ' (no End here; Event returns to scheduler automatically)
