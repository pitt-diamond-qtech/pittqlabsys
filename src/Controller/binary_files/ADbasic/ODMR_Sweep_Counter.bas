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
' This script generates a voltage ramp on DAC1 for SG384 modulation input
' and counts photons synchronously during the sweep.
'
' IMPORTANT: Voltage is constrained to ±1V for SG384 compatibility
' DAC operates at ±10V range for precision, but output is clamped to ±1V
'
#Include ADwinGoldII.inc

Rem ============================================================
Rem Triangle DAC sweep with per-step counts on Counter 1 (falling edges)
Rem For SG384 Enhanced Sweep Mode - provides triangle waveform to modulation input
Rem Exposed to Python:
Rem   Data_1[] : counts per step
Rem   Data_2[] : DAC digits per step
Rem   Par_20   : sweep ready flag (1=ready for Python to read; clear to 0 to continue)
Rem   Par_21   : number of points in last sweep
Rem Parameters from Python:
Rem   FPar_1 = Vmin [V] (typically -1.0V for SG384)
Rem   FPar_2 = Vmax [V] (typically +1.0V for SG384)
Rem   Par_1  = N_STEPS (>=2)
Rem   Par_2  = SETTLE_US
Rem   Par_3  = DWELL_US
Rem   Par_4  = DAC_CH (1..2)
Rem   Par_10 = START (1=run, 0=stop)
Rem ============================================================

Rem --- helper functions ---
Function VoltsToDigits(v) As Long
  VoltsToDigits = Round((v + 10.0) * 65535.0 / 20.0)
EndFunction

Dim i, n_steps, n_points, k As Long
Dim dac_ch As Long
Dim settle_us, dwell_us As Long
Dim last_cnt, cur_cnt, delta As Long
Dim vmin_dig, vmax_dig, step_dig As Long
Dim pos As Long
Dim ready As Long

Rem Allocate generous global buffers (PC reads the first Par_21 entries)
Rem Data_1: counts per step
Dim Data_1[200000] As Long
Rem Data_2: dac digits per step  
Dim Data_2[200000] As Long

Init:
  Rem optional: set a modest Processdelay; timing uses P1_Sleep anyway
  Processdelay = 10000

  Rem --- configure Counter 1 for falling-edge counting ---
  Rem Stop, clear, and set mode: clock/direction, invert A/CLK; enable CLR/LATCH input disabled.
  Cnt_Enable(0)
  Cnt_Clear(0001b)

  Rem Mode bits (see manual): bit0=0 (clock/dir), bit2=1 (invert A/CLK), bit3=0 (DIR not inverted)
  Rem bits4-5=0 (use CLR input disabled), others 0.
  Cnt_Mode(1, 00000100b)
  Rem single-ended on all inputs
  Cnt_SE_Diff(0000b)
  Rem start counter 1
  Cnt_Enable(0001b)

  Rem --- initialize watchdog (50ms timeout, all actions armed) ---
  Watchdog_Init(1, 5000, 1111b)

  Rem init handshake
  Par_20 = 0
  Par_21 = 0
  last_cnt = 0

Event:

  If (Par_10 = 0) Then
    Rem idle – keep comms alive
    Exit
  EndIf

  Rem --- snapshot parameters from Python (allows tweaking between sweeps) ---
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

  vmin_dig  = VoltsToDigits(FPar_1)
  vmax_dig  = VoltsToDigits(FPar_2)

  Rem total points in triangle sweep (up and down, no repeated endpoints)
  n_points = (2 * n_steps) - 2
  IF (n_points < 2) THEN
    n_points = 2
  ENDIF
  Par_21 = n_points

  Rem Preload DAC to the first code so the first settle applies correctly
  Write_DAC(dac_ch, vmin_dig)
  Start_DAC()

  Rem Re-base the incremental counting window
  Cnt_Latch(0001b)
  last_cnt = Cnt_Read_Latch(0001b)

  Rem ---- Sweep loop ----
  For k = 0 To (n_points - 1)

    Rem position index along the triangle (0..n_steps-1..1)
    IF (k < n_steps) THEN pos = k ELSE pos = (2 * n_steps) - 2 - k
        
    Rem DAC code for this step
    IF (n_steps > 1) THEN step_dig = ((vmax_dig - vmin_dig) * pos) / (n_steps - 1) ELSE step_dig = 0
    Data_2[k+1] = vmin_dig + step_dig

    Rem Output the step
    Write_DAC(dac_ch, Data_2[k+1])
    Start_DAC()

    Rem Settle after step change
    IF (settle_us > 0) THEN
      P1_Sleep(settle_us * 100)
    ENDIF
      
    Rem Count during dwell window:
    Rem   Latch AFTER the dwell to get the integrated number of edges over dwell
    IF (dwell_us > 0) THEN
      P1_Sleep(dwell_us * 100)
    ENDIF
    Cnt_Latch(0001b)
    cur_cnt = Cnt_Read_Latch(0001b)

    Rem 32-bit wrap handling (do in Float to avoid overflow)
    Dim fd As Float
    fd = cur_cnt - last_cnt
    IF (fd < 0.0) THEN
      fd = fd + 4294967296.0
    ENDIF
    Data_1[k+1] = Round(fd)
    last_cnt = cur_cnt

    Rem reset watchdog after each step to prevent timeout
    Watchdog_Reset()
  Next k

  Rem Signal to Python that one sweep is ready; wait until it clears the flag.
  Par_20 = 1
  DO
    Rem short sleep to avoid hogging bus while waiting
    Rem 10 us
    P1_Sleep(1000)
    Rem reset watchdog during PC handshake to prevent timeout
    Watchdog_Reset()
  LOOP UNTIL (Par_20 = 0) OR (Par_10 = 0)

  Rem loop continues immediately for next sweep if Par_10 stays 1
  End