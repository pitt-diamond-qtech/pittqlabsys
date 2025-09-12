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
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Duttlab
'<Header End>
'This script enables counting on counter 1.
'The bin size is directly related to the process delay ie. the time between clearing the
'counter is delay*3.3ns. A larger delay is neccesary to make the bins adequatly sized.

#Include ADwinGoldII.inc

init:
  Cnt_Enable(0)   'disables/stops counting on counter 1
  Cnt_Clear(1)    'sets counter 1 to zero
  Cnt_Mode(1,8)   'sets counter 1 to increment on falling edge; equivalent to Cnt_Mode(1,0001)
  Cnt_Enable(1)   'enables counting on counter 1
  
Event:
  Par_1 = Cnt_Read(1)   'Sets integer_variable_1 to counter 1 value
  Cnt_Clear(1)          'sets counter 1 t zero
  
Finish:
  Cnt_Enable(0)
  
  
