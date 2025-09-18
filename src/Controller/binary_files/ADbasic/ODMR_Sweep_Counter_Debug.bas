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
' ODMR Sweep Counter Script - DEBUG VERSION
' This script helps diagnose counting issues by providing detailed diagnostics
'
#Include ADwinGoldII.inc

Rem ============================================================
Rem Triangle DAC sweep with per-step counts on Counter 1 (falling edges)
Rem For SG384 Enhanced Sweep Mode - provides triangle waveform to modulation input
Rem DEBUG VERSION with additional monitoring parameters
Rem Exposed to Python:
Rem   Data_1[] : counts per step
Rem   Data_2[] : DAC digits per step
Rem   Par_20   : sweep ready flag (1=ready for Python to read; clear to 0 to continue)
Rem   Par_21   : number of points in last sweep
Rem   Par_22   : DEBUG: Current step index (0 to n_points-1)
Rem   Par_23   : DEBUG: Current position in triangle (0 to n_steps-1)
Rem   Par_24   : DEBUG: Current voltage in volts
Rem   Par_25   : DEBUG: Event cycle counter
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
Function VoltsToDigits(v)
  VoltsToDigits = Round((v + 10.0) * 65535.0 / 20.0)
EndFunction

Function DigitsToVolts(d)
  DigitsToVolts = (d * 20.0 / 65535.0) - 10.0
EndFunction

Dim i, n_steps, n_points, k As Long
Dim dac_ch As Long
Dim settle_us, dwell_us As Long
Dim last_cnt, cur_cnt, delta As Long
Dim vmin_dig, vmax_dig, step_dig As Long
Dim pos As Long
Dim ready As Long
Dim event_cycle As Long
Dim current_voltage As Float

Rem Allocate generous global buffers (PC reads the first Par_21 entries)
Dim Data_1[200000] As Long   Rem counts
Dim Data_2[200000] As Long   Rem dac digits

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
  Cnt_SE_Diff(0000b)         Rem single-ended on all inputs
  Cnt_Enable(0001b)          Rem start counter 1

  Rem init handshake and debug parameters
  Par_20 = 0
  Par_21 = 0
  Par_22 = 0
  Par_23 = 0
  Par_24 = 0.0
  Par_25 = 0
  last_cnt = 0
  event_cycle = 0

Event:
  Rem Increment event cycle counter
  event_cycle = event_cycle + 1
  Par_25 = event_cycle

  If (Par_10 = 0) Then
    Rem idle – keep comms alive
    Return
  EndIf

  Rem --- snapshot parameters from Python (allows tweaking between sweeps) ---
  n_steps   = Par_1
  If (n_steps < 2) Then n_steps = 2 EndIf
  settle_us = Par_2
  dwell_us  = Par_3
  dac_ch    = Par_4
  If (dac_ch < 1) Then dac_ch = 1 EndIf
  If (dac_ch > 2) Then dac_ch = 2 EndIf

  vmin_dig  = VoltsToDigits(FPar_1)
  vmax_dig  = VoltsToDigits(FPar_2)

  Rem total points in triangle sweep (up and down, no repeated endpoints)
  n_points = (2 * n_steps) - 2
  If (n_points < 2) Then n_points = 2 EndIf
  Par_21 = n_points

  Rem Preload DAC to the first code so the first settle applies correctly
  Write_DAC(dac_ch, vmin_dig)
  Start_DAC()

  Rem Re-base the incremental counting window
  Cnt_Latch(0001b)
  last_cnt = Cnt_Read_Latch(0001b)

  Rem ---- Sweep loop ----
  For k = 0 To (n_points - 1)

    Rem DEBUG: Update monitoring parameters
    Par_22 = k
    Par_23 = pos

    Rem position index along the triangle (0..n_steps-1..1)
    If (k < n_steps) Then
      pos = k
    Else
      pos = (2 * n_steps) - 2 - k
    EndIf

    Rem DAC code for this step
    If (n_steps > 1) Then
      step_dig = ((vmax_dig - vmin_dig) * pos) / (n_steps - 1)
    Else
      step_dig = 0
    EndIf
    Data_2[k+1] = vmin_dig + step_dig

    Rem DEBUG: Calculate and store current voltage
    current_voltage = DigitsToVolts(Data_2[k+1])
    Par_24 = current_voltage

    Rem Output the step
    Write_DAC(dac_ch, Data_2[k+1])
    Start_DAC()

    Rem Settle after step change
    If (settle_us > 0) Then
      P1_Sleep(settle_us * 100)
    EndIf

    Rem Count during dwell window:
    Rem   Latch AFTER the dwell to get the integrated number of edges over dwell
    If (dwell_us > 0) Then
      P1_Sleep(dwell_us * 100)
    EndIf
    Cnt_Latch(0001b)
    cur_cnt = Cnt_Read_Latch(0001b)

    Rem delta with 32-bit wrap handling
    delta = cur_cnt - last_cnt
    If (delta < 0) Then
      Rem wrap-around correction for unsigned 32-bit hardware counter
      delta = delta + 4294967296
    EndIf
    Data_1[k+1] = delta
    last_cnt = cur_cnt

    Rem (optional) watchdog reset could be placed here if you use it
    Rem Watchdog_Reset()
  Next k

  Rem Signal to Python that one sweep is ready; wait until it clears the flag.
  Par_20 = 1
  Do
    Rem short sleep to avoid hogging bus while waiting
    P1_Sleep(1000)  Rem 10 us
  Loop While (Par_20 <> 0 And Par_10 <> 0)

  Rem loop continues immediately for next sweep if Par_10 stays 1
  Return