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

' Global parameters
Dim Par_10 As Long    ' START flag
Dim Par_20 As Long    ' READY flag  
Dim Par_21 As Long    ' Number of points
Dim Par_22 As Long    ' Current step
Dim Par_23 As Long    ' Position in triangle
Dim Par_24 As Float   ' Current voltage
Dim Par_25 As Long    ' Event cycle counter

' Initialize parameters
Par_10 = 0
Par_20 = 0
Par_21 = 0
Par_22 = 0
Par_23 = 0
Par_24 = 0.0
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
    Par_24 = -1.0  ' Start voltage
    
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
