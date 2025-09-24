'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 150000000
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

' Hello Heartbeat Script
' This script sets Par_25 to 0 and Par_80 to 4242
' and increments Par_25 every Event

' Internal variables only (Par_n and FPar_n are reserved by ADbasic)

Init:
  Par_25 = 0
  Par_80 = 4242

Event:
  Par_25 = Par_25 + 1
End
