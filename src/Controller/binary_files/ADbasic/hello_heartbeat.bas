'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 300000
' Eventsource                    = Timer
' Priority                       = Normal
' Version                        = 1
' ADbasic_Version                = 6.3.0
'<Header End>


' Hello Heartbeat Script
' This script sets Par_25 to 0 and Par_80 to 4242
' and increments Par_25 every Event

' Internal variables only (Par_n and FPar_n are reserved by ADbasic)

Init: 
  ' Force a known periodic rate: ~1 ms on Gold-II (T11).
  ' (On T11, 1 ms ≈ 303000 ticks; 300000 is ≈ 0.99 ms.)
  Processdelay = 300000 
  Par_25 = 0 ' heartbeat counter
  Par_80 = 4242 ' signature to confirm script is loaded
  Par_71 = Processdelay
  Par_72 = 1000    ' second counter to confirm Event is ticking
  Par_78 = 0                  ' toggle variable to confirm Event is ticking

Event:
  Par_25 = Par_25 + 1
  Par_72 = Par_72 + 10
  IF (Par_78 = 0) THEN
    Par_78 = 1
  ELSE
    Par_78 = 0
  ENDIF

Finish:
  Par_25 = 0
