'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 3000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = SINGLENV-PC-1  SINGLENV-PC-1\Duttlab
'<Header End>
#Include ADwinGoldII.inc
DIM number_of_signal_events AS LONG
DIM iteration_number, trigger_duration, i, j as LONG
DIM count_time, reset_time, sequence_duration AS FLOAT
DIM delay AS FLOAT
DIM Data_1[100000] AS LONG ' 100000 is the maximum number of iterations
DIM Data_2[100000] AS LONG ' 100000 is the maximum number of iterations

init:
  Cnt_Enable(0)
  Cnt_Mode(1,8)   ' Counter 1 set to increasing
  Par_7 = 0       ' acquisition done flag
  Par_8 = 0       ' repetition_counter
  number_of_signal_events = Par_5 * Par_6
  trigger_duration = 12
  Cnt_Clear(1)          ' Clear counter 1
  iteration_number = 0
  ' NOTE: The offsets (10 and 30) are historical calibration values
  ' that were determined empirically. The actual timing values are:
  ' count_time = (Par_3-10)/10  where Par_3 is passed from Python
  ' These offsets ensure proper timing calibration for the hardware setup.
  count_time = 30
  reset_time = 1400/10 
  sequence_duration = Par_9/10 ' since Par_9 is given in ns and IO_Sleep accepts params in 10ns, we divide by 10
  Conf_DIO(1100b) ' configure 0 - 15 as DIGIN, and 16 - 31 as DIGOUT
  ' Set digital output 21 to low (no trigger)
  DIGOUT(21, 0)
  DIGOUT(28, 0)              ' Set trigger debug low
  delay = (1544 + 10 + 12) * 3 ' * 10 since the variables are in 10 ns and /(10/3) as the value has to be in number or clock ticks which is 10/3 for T11 processor
  Processdelay = delay
  i = 0
  DO
    Data_1[i] = 0 '20 data points
    Data_2[i] = 0 '20 data points
    i = i +1
  UNTIL (i = 100000)
event:
  j = 0
  Par_8 = Par_8 + 1          ' current event number (increase for signal count)
  DIGOUT(21, 1)              ' Set trigger high
  DIGOUT(28, 1)
  IO_Sleep(trigger_duration)
  DIGOUT(21, 0)              ' Set trigger low
  DIGOUT(28, 0)
  Cnt_Enable(1)          ' enable counter 1
  IO_Sleep(1200) ' 10000 + 1230 = 11230
  DIGOUT(16, 1)
  Cnt_Clear(1)           ' Clear counter 
  IO_Sleep(count_time)
  Data_1[iteration_number] = Data_1[iteration_number] + Cnt_Read(1) 
  IO_Sleep(140)       ' accumulate sig
  Cnt_Clear(1)           ' Clear counter
  IO_Sleep(count_time)
  Data_2[iteration_number] = Data_2[iteration_number] + Cnt_Read(1)        ' accumulate ref
  DIGOUT(16, 0)
  Cnt_Enable(0)
  iteration_number = iteration_number + 1 ' Since Data_1 and Data_2 start at index 1
  ' Check if we've completed all repetitions and if iteration_number is 0 which means that it got to Par_6
  ' Par_5 contains the number of repetitions per scan point (e.g., 50000)
  IF (Par_8 = number_of_signal_events) THEN
    Par_7=1
    Cnt_Enable(0)
    DIGOUT(21, 0)                  ' Ensure trigger is low
    END
  ENDIF
