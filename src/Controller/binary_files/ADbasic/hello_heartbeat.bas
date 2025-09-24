'<ADbasic Header, Headerversion 001.001>
' Process_Number               = 1
' Initial_Processdelay         = 20000
' Eventsource                  = Timer
' Control_long_Delays_for_Stop = No
' Priority                     = Normal
' ADbasic_Version              = 6.3.0
'<Header End>

' No includes, no functions

Init:
  Par_25 = 0
  Par_99 = 4242
  ' signature so we know this TB1 is actually loaded

Event:
  Par_25 = Par_25 + 1
End
