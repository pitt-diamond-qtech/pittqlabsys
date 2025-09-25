' <ADbasic Header, Headerversion 001.001>
' Process_Number         = 1
' Initial_Processdelay   = 300000
' Eventsource            = Timer
' Priority               = Normal
' ADbasic_Version        = 6.3.0
' <Header End>

' If your project uses the vendor include, keep it:
#Include ADwinGoldII.inc

Init:
' *** Disable any armed board watchdog from previous code ***
  Watchdog_Init(0, 0, 0)
  Processdelay = 300000
  Par_80 = 4242     ' signature
  Par_25 = 0        ' heartbeat
  Par_71 = Processdelay
  Par_60 = 0        ' trace: where did we get to?
  Par_72 = 1000     ' trace counter 2

Event:
  Par_60 = 101      ' entered Event
  Par_25 = Par_25 + 1
  Par_72 = Par_72 + 10
  Par_60 = 199      ' exiting Event


Finish:
  Par_60 = 900      ' Finish ran because process stopped
