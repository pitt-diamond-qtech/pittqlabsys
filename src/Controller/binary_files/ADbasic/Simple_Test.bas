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

' Simple ADbasic Test Script
' This script just sets some parameters and runs a basic loop

' Internal variables only (Par_n and FPar_n are reserved by ADbasic)
Dim counter As Long   ' Internal counter

Init:
  ' Initialize parameters (Par_n and FPar_n are reserved by ADbasic)
  Par_10 = 0
  Par_20 = 0
  Par_21 = 0
  counter = 0

' Main event loop
Event:
  ' Increment counter
  counter = counter + 1
  Par_21 = counter
  
  ' Check if we should stop
  IF (Par_10 = 0) THEN
    Par_20 = 0
  ELSE
    Par_20 = 1
  ENDIF
  
  ' Small delay
  IO_Sleep(1000)  ' 10 us delay
  
  ' Continue loop
  Goto Event

' Cleanup (should never reach here)
Finish:
  Par_20 = 0
  End
