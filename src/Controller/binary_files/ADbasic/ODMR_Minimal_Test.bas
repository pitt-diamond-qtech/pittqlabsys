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
'<Header End>

#Include ADwinGoldII.inc

' Minimal ODMR Test Script
' This script removes hardware initialization to test basic functionality

' Internal variables only (Par_n and FPar_n are reserved by ADbasic)
' No Dim statements needed for Par_n or FPar_n variables

Init:
    ' Initialize parameters (Par_n and FPar_n are reserved by ADbasic)
    Par_10 = 0
    Par_20 = 0
    Par_21 = 0
    Par_22 = 0
    Par_23 = 0
    FPar_24 = 0.0
    Par_25 = 0

' Main event loop
Event:
  ' Increment event counter
  Par_25 = Par_25 + 1
  
  ' Check if we should run a sweep
  IF (Par_10 = 1) THEN
    ' Simulate a simple sweep
    Par_21 = 18  ' Number of points
    Par_22 = 0   ' Current step
    Par_23 = 0   ' Position
    FPar_24 = -1.0  ' Start voltage
    
    ' Simulate sweep completion
    Par_20 = 1   ' Ready flag
    Par_10 = 0   ' Stop
  ELSE
    Par_20 = 0   ' Not ready
  ENDIF
  
  ' Small delay
  IO_Sleep(1000)  ' 10 us delay
  
  ' Continue loop
  Goto Event

' Cleanup
Finish:
  Par_20 = 0
  End
