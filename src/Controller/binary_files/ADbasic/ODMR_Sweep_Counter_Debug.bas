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
' ODMR Sweep Counter Script — DEBUG (array-based step diagnostics)
' Triangle on DACx; counts falling edges on Counter 1.
' Non-blocking handshake: Par_20=1 when ready; PC must clear to 0.

#Include ADwinGoldII.inc

'================= Interface =================
' From Python:
'   FPar_1 = Vmin [V] (clamped to [-1,+1])
'   FPar_2 = Vmax [V] (clamped to [-1,+1])
'   Par_1  = N_STEPS   (>=2)
'   Par_2  = SETTLE_US (µs)
'   Par_3  = DWELL_US  (µs)
'   Par_4  = DAC_CH    (1..2)
'   Par_10 = START     (1=run, 0=idle)
' To Python:
'   Data_1[]  = counts per step (LONG)
'   Data_2[]  = DAC digits per step (LONG)
'   FData_1[] = volts per step (FLOAT)
'   Data_3[]  = triangle pos per step (LONG)
'   Par_20    = ready flag (1=data ready)
'   Par_21    = number of points (2*N_STEPS-2)
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

'--- working vars ---
Dim n_steps, n_points, k As Long
Dim dac_ch As Long
Dim settle_us, dwell_us As Long
Dim last_cnt, cur_cnt As Long
Dim vmin_dig, vmax_dig As Long
Dim step_dig, pos As Long
Dim fd As Float
Dim vmin_clamped, vmax_clamped, t As Float
Dim sum_counts, max_counts, max_idx As Long

'--- result buffers (1-based indexing) ---
Dim Data_1[200000]  As Long   ' counts per step
Dim Data_2[200000]  As Long   ' DAC digits per step
Dim FData_1[200000] As Float  ' volts per step
Dim Data_3[200000]  As Long   ' triangle pos per step

Init:
  Processdelay = 10000

  ' Counter 1: clk/dir, invert A/CLK => count falling edges
  Cnt_Enable(0)
  Cnt_Clear(0001b)
  Cnt_Mode(1, 00000100b)   ' bit0=0 clk/dir, bit2=1 invert A/CLK
  Cnt_SE_Diff(0000b)
  Cnt_Enable(0001b)

  ' Watchdog (debug): 1 s (units = 10 µs)
  Watchdog_Init(1, 100000, 1111b)

  Par_20 = 0
  Par_21 = 0
  Par_25 = 0
  Par_30 = 0
  Par_31 = 0
  Par_32 = 0
  FPar_33 = 0.0
  last_cnt = 0

Event:
  ' heartbeat
  Par_25 = Par_25 + 1

  ' idle when STOP
  IF (Par_10 = 0) THEN
    IO_Sleep(1000)
    Watchdog_Reset()

  ELSE
    ' non-blocking handshake: if previous data not read, idle
    IF (Par_20 <> 0) THEN
      IO_Sleep(1000)
      Watchdog_Reset()

    ELSE
      ' -------- run ONE triangle sweep --------

      ' 1) snapshot params
      n_steps   = Par_1
      IF (n_steps < 2) THEN n_steps = 2 ENDIF
      settle_us = Par_2
      dwell_us  = Par_3
      dac_ch    = Par_4
      IF (dac_ch < 1) THEN dac_ch = 1 ENDIF
      IF (dac_ch > 2) THEN dac_ch = 2 ENDIF

      ' 2) clamp & order
      vmin_clamped = FPar_1
      vmax_clamped = FPar_2
      IF (vmin_clamped < -1.0) THEN vmin_clamped = -1.0 ENDIF
      IF (vmin_clamped >  1.0) THEN vmin_clamped =  1.0 ENDIF
      IF (vmax_clamped < -1.0) THEN vmax_clamped = -1.0 ENDIF
      IF (vmax_clamped >  1.0) THEN vmax_clamped =  1.0 ENDIF
      IF (vmin_clamped > vmax_clamped) THEN
        t = vmin_clamped : vmin_clamped = vmax_clamped : vmax_clamped = t
      ENDIF

      ' 3) digits
      vmin_dig = VoltsToDigits(vmin_clamped)
      vmax_dig = VoltsToDigits(vmax_clamped)
      IF (vmin_dig = vmax_dig) THEN n_steps = 2 ENDIF

      ' 4) points & preload
      n_points = (2 * n_steps) - 2
      IF (n_points < 2) THEN n_points = 2 ENDIF
      Par_21 = n_points

      Write_DAC(dac_ch, vmin_dig)
      Start_DAC()

      Cnt_Latch(0001b)
      last_cnt = Cnt_Read_Latch(1)

      sum_counts = 0
      max_counts = -2147483648   ' lowest LONG
      max_idx    = 0

      ' 5) sweep
      For k = 0 To (n_points - 1)

        ' triangle position
        IF (k < n_steps) THEN
          pos = k
        ELSE
          pos = (2 * n_steps) - 2 - k
        ENDIF

        ' step digits
        IF (n_steps > 1) THEN
          step_dig = ((vmax_dig - vmin_dig) * pos) / (n_steps - 1)
        ELSE
          step_dig = 0
        ENDIF
        Data_2[k+1]  = vmin_dig + step_dig
        FData_1[k+1] = DigitsToVolts(Data_2[k+1])
        Data_3[k+1]  = pos

        ' output
        Write_DAC(dac_ch, Data_2[k+1])
        Start_DAC()

        ' settle
        IF (settle_us > 0) THEN
          IO_Sleep(settle_us * 100)
        ENDIF

        ' dwell
        IF (dwell_us > 0) THEN
          IO_Sleep(dwell_us * 100)
        ENDIF

        ' latch & read
        Cnt_Latch(0001b)
        cur_cnt = Cnt_Read_Latch(1)

        ' wrap-safe delta
        fd = cur_cnt - last_cnt
        IF (fd < 0.0) THEN
          fd = fd + 4294967296.0
        ENDIF
        Data_1[k+1] = Round(fd)
        last_cnt = cur_cnt

        ' summaries
        sum_counts = sum_counts + Data_1[k+1]
        IF (Data_1[k+1] > max_counts) THEN
          max_counts = Data_1[k+1]
          max_idx = k
        ENDIF

        Watchdog_Reset()
      Next k

      ' 6) end-of-sweep summaries
      Par_30  = sum_counts
      Par_31  = max_counts
      Par_32  = max_idx
      IF (n_points > 0) THEN
        FPar_33 = sum_counts / n_points
      ELSE
        FPar_33 = 0.0
      ENDIF

      ' 7) signal ready — non-blocking
      Par_20 = 1

      ' return; PC clears Par_20 to 0 to release next sweep
    ENDIF
  ENDIF
  ' (no End here)
