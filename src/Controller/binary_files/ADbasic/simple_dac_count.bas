'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 300000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = Normal
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
'<Header End>

#Include ADwinGoldII.inc

Rem =======================
Rem Parameters (PC -> DSP)
Rem   FPar_1  : Output voltage on DAC (Volts)   [-10..+10]
Rem   Par_1   : DWELL_US (microseconds)
Rem   Par_2   : SETTLE_US (microseconds)
Rem   Par_4   : EDGE mode (0=rising, 1=falling)
Rem   Par_5   : DAC channel (1..2)
Rem   Par_6   : DIR sense (0=DIR Low=up, 1=DIR High=up)
Rem   Par_10  : START (1=do one measurement, 0=idle)
Rem
Rem Results (DSP -> PC)
Rem   Par_20  : READY flag (1=result ready, host must clear to 0)
Rem   Par_21  : COUNTS measured in the dwell window
Rem   Par_22  : last_cnt (debug)
Rem   Par_23  : cur_cnt (debug)
Rem   Par_24  : raw delta (debug)
Rem   Par_25  : heartbeat
Rem   Par_71  : Processdelay (ticks of 10 ns)
Rem   Par_80  : signature (4242)
Rem =======================

Function VoltsToDigits(v) As Long
  Rem clamp to the DAC range [-10V, +10V]
  IF (v < -10.0) THEN
    v = -10.0
  ENDIF
  IF (v > 10.0) THEN
    v = 10.0
  ENDIF
  VoltsToDigits = Round((v + 10.0) * 65535.0 / 20.0)
EndFunction

Dim settle_us, dwell_us As Long
Dim dac_ch, edge_mode As Long
Dim last_cnt, cur_cnt As Long
Dim fd As Float
Dim dig As Long
Rem store the last result for easy array readback
Dim Data_1[8] As Long   
Dim FData_1[8] As Float   

Init:
  Rem ~1 ms loop @ 10 ns tick
  Processdelay = 300000        
  Par_71 = Processdelay
  Par_80 = 4242
  Par_20 = 0
  Par_21 = 0
  Par_25 = 0

  Rem pre-configure counter single-ended
  Cnt_SE_Diff(0000b)

Event:
  Rem heartbeat
  Par_25 = Par_25 + 1

  IF (Par_10 = 0) THEN
    Rem idle; keep breathing gently
    Rem 10 µs
    IO_Sleep(1000)   
  ELSE
    Rem ---- snapshot settings ----
    dwell_us  = Par_1
    settle_us = Par_2
    dac_ch    = Par_5
    edge_mode = Par_4
    IF (dac_ch < 1) THEN
      dac_ch = 1
    ENDIF
    IF (dac_ch > 2) THEN
      dac_ch = 2
    ENDIF

    Rem ---- program DAC ----
    dig = VoltsToDigits(FPar_1)
    Write_DAC(dac_ch, dig)
    Start_DAC()

    Rem ---- program counter mode each shot ----
    Cnt_Enable(0)
    Cnt_Clear(0001b)
    IF (edge_mode = 0) THEN
      Rem rising edges
      IF (Par_6 = 1) THEN
        Cnt_Mode(1, 00000000b)
      ELSE
        Cnt_Mode(1, 00001000b)
      ENDIF
    ELSE
      Rem falling edges
      IF (Par_6 = 1) THEN
        Cnt_Mode(1, 00000100b)
      ELSE
        Cnt_Mode(1, 00001100b)
      ENDIF
    ENDIF
    Cnt_Enable(0001b)

    Rem ---- settle, then open the dwell window ----
    IF (settle_us > 0) THEN
      IO_Sleep(settle_us * 100)
    ENDIF

    Cnt_Latch(0001b)
    last_cnt = Cnt_Read_Latch(1)

    IF (dwell_us > 0) THEN
      IO_Sleep(dwell_us * 100)
    ENDIF

    Cnt_Latch(0001b)
    cur_cnt = Cnt_Read_Latch(1)

    Rem ---- compute delta with wrap handling using Float arithmetic ----
    Rem Convert to Float explicitly to avoid type issues
    fd = cur_cnt - last_cnt
    
    Rem Debug: store raw counter values for analysis
    Rem store last_cnt for debugging
    Par_22 = last_cnt    
    Rem store cur_cnt for debugging
    Par_23 = cur_cnt     
    Rem store raw delta for debugging
    Par_24 = fd          
    
    IF (fd < 0.0) THEN    
      Rem hardware is unsigned 32-bit     
      ' modulo 2^32 into [0,2^32)      
      fd = fd + 4294967296.0
    ENDIF

    ' Direction-agnostic: pick the smaller arc on the 32-bit ring

    IF (fd > 2147483647.0) THEN ' > 2^31
      fd = 4294967296.0 - fd     ' take the other way around
    ENDIF
    
    Rem safe INT result
    Data_1[1]  = Round(fd)          
    Rem exact (prefer reading this from Python)
    FData_1[1] = fd                 
    Rem quick check path
    Par_21 = Data_1[1]              

    Rem one-shot ready handshake
    Par_20 = 1
    DO
      Rem 10 µs wait for host to grab result
      IO_Sleep(1000)   
    UNTIL ((Par_20 = 0) OR (Par_10 = 0))

    Rem auto-return to idle so the host must re-arm START explicitly
    Par_10 = 0
  ENDIF
