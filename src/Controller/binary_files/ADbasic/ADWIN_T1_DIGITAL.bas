'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 1000
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
'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 1000
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
' adwin_triggering_proteus.bas
' This process generates trigger pulses to control proteus external triggering
' for testing the ADwin -> proteus control architecture.
'
' Hardware Setup:
' - ADwin Digital Output -> Proteus TRIG 1 IN (front panel)
' - Proteus configured for external trigger with Wait Trigger enabled
' - Computer controls JUMP_MODE software for sequence advancement
' for this file, we use cpu_sleep for wait
' Operation:
' - Process generates trigger pulses at specified intervals
' - Each trigger causes Proteus to advance to next sequence line
' - Computer can control timing and number of triggers via parameters
' This is the new approach: adwin triggers awg to move to next task/line

' Variables exchanged with python
' Par_5: repeat_count
' Par_6: number of iterations
' Par_7: acquisition done flag
' Par_8: repetition_counter
' Data_1: signal counts
' Data_2: reference counts
' Par_9: sequence_duration (with calibration offset): Time of the awg sequence
' Par_10: proteus response delay

#Include ADwinGoldII.inc
DIM number_of_signal_events AS LONG
DIM iteration_number, i as LONG
DIM count_time, sequence_duration, sleep_duration AS FLOAT
DIM laser_init, delay, proteus_response, aom_delay, sleep_to_count, count_plus_ref AS FLOAT
DIM Data_1[20] AS LONG ' 100000 is the maximum number of iterations
DIM Data_2[20] AS LONG ' 100000 is the maximum number of iterations

init:
  Cnt_Enable(0)
  Cnt_Mode(1,8)   ' Counter 1 set to increasing
  Par_7 = 0       ' acquisition done flag
  Par_8 = 0       ' repetition_counter
  number_of_signal_events = Par_5 * Par_6
  

  Cnt_Clear(1)          ' Clear counter 1
  iteration_number = 0
  ' NOTE: The offsets (10 and 30) are historical calibration values
  ' that were determined empirically. The actual timing values are:
  ' These offsets ensure proper timing calibration for the hardware setup.
  aom_delay = 936.65/10
  count_time = Par_3
  laser_init = Par_4
  sequence_duration = Par_9/10
  proteus_response = Par_10/10
  sleep_duration = (Par_9 - laser_init - 2*count_time)/190
  count_time = (count_time)/10 
  laser_init = laser_init/10
  Conf_DIO(1100b) ' configure 0 - 15 as DIGIN, and 16 - 31 as DIGOUT
  ' Set digital output 21 to low (no trigger)
  DIGOUT(16, 0)
  DIGOUT(28, 0)
  count_plus_ref = 2*count_time
  sleep_to_count = aom_delay - count_plus_ref
  delay = (sequence_duration + aom_delay +100) * 3 ' * 10 since the variables are in 10 ns and /(10/3) as the value has to be in number or clock ticks which is 10/3 for T11 processor
  Processdelay = delay
  i = 1
  DO
    Data_1[i] = 0 '20 data points
    Data_2[i] = 0 '20 data points
    i = i +1
  UNTIL (i = 21)
event:
  Cnt_Enable(0)
  Cnt_Clear(1)
  sleep_duration = sleep_duration*iteration_number
  Par_8 = Par_8 + 1          ' current event number (increase for signal count)
  iteration_number = iteration_number + 1 ' Since Data_1 and Data_2 start at index 1
  Write_DAC(1, iteration_number*1000)
  Start_DAC()
  DIGOUT(28, 1)              ' Set trigger debug high
  CPU_Sleep(laser_init)
  DIGOUT(28, 0)              ' Set trigger debug low
  CPU_Sleep(sleep_duration)
  DIGOUT(28, 1)   
  CPU_Sleep(count_plus_ref)
  DIGOUT(28, 0)  
  CPU_Sleep(sleep_to_count)
  DIGOUT(16, 1)
  Cnt_Enable(1)          ' enable counter 1
  CPU_Sleep(count_time)          ' count time 300 ns
  Cnt_Latch(1)           ' Latch counter 1
  CPU_Sleep(count_time)          ' count time 300 ns
  Cnt_Enable(0)          ' disable counter 1
  DIGOUT(16, 0)
  Data_1[iteration_number] = Data_1[iteration_number] + Cnt_Read_Latch(1)  ' accumulate sig
  Data_2[iteration_number] = Data_2[iteration_number] + Cnt_Read(1)        ' accumulate sig+ref
  Cnt_Clear(1)           ' Clear counter 
  
  IF (iteration_number = Par_6) THEN 'if we did all of our iterations for a given sequence, then go back to iteration 0
    iteration_number = 0
  ENDIF
  ' Check if we've completed all repetitions and if iteration_number is 0 which means that it got to Par_6
  ' Par_5 contains the number of repetitions per scan point (e.g., 50000)
  IF (Par_8 = number_of_signal_events) THEN
    Par_7=1
    Cnt_Enable(0)
    DIGOUT(28, 0)                  ' Ensure trigger is low
    END
  ENDIF
