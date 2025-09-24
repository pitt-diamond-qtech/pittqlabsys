'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 20000
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

' Hello Heartbeat Script
' This script sets Par_25 to 0 and Par_80 to 4242
' and increments Par_25 every Event

' Internal variables only (Par_n and FPar_n are reserved by ADbasic)

Init: 
  ' Force a known periodic rate: ~1 ms on Gold-II (T11).
  ' (On T11, 1 ms ≈ 303000 ticks; 300000 is ≈ 0.99 ms.)
  Processdelay = 300000
  Par_25 = 0
  Par_80 = 4242
  Par_71 = Processdelay

Event:
  Par_25 = Par_25 + 1
End
