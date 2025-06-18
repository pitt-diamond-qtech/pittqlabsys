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
'This script enables counting on counter 1 with averaging.
'The bin size is directly related to the process delay ie. the time between clearing the
'counter is delay*3.3ns. A larger delay is neccesary to make the bins adequatly sized.

#Include ADwinGoldII.inc
#Define summed_counts Par_2 'gets total counts over a number of cycles
#Define num_cycles Par_10   'how many cycles to average over
#Define total_counts Par_5  'variable to store total counts over a number of cycles
DIM index AS LONG

init:
  Cnt_Enable(0)   'disables/stops counting on counter 1
  Cnt_Clear(1)    'sets counter 1 to zero
  Cnt_Mode(1,8)   'sets counter 1 to increment on falling edge; equivalent to Cnt_Mode(1,0001)
  Cnt_Enable(1)   'enables counting on counter 1
  index = 1
  summed_counts = 0
  total_counts = 0
  
Event:
  IF (index > Par_10) THEN
    total_counts = summed_counts  'to ensure the adwin is only reading the counts after 10 cycles
    summed_counts = 0
    index = 1
  ENDIF
  
  Par_1 = Cnt_Read(1)   'Sets integer_variable_1 to counter 1 value
  summed_counts = summed_counts + Par_1
  Cnt_Clear(1)
  Inc(index)
  
Finish:
  Cnt_Enable(0)
  
  
