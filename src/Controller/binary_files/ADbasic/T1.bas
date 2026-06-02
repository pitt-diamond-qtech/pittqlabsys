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
' for this file, we use IO_Sleep for wait
' Operation:
' - Process generates trigger pulses at specified intervals
' - Each trigger causes Proteus to advance to next sequence line
' - Computer can control timing and number of triggers via parameters
' This is the new approach: adwin triggers awg to move to next task/line

' Variables exchanged with python
' Par_3: count_time (with calibration offset)
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
DIM count_time, ref_counts, sig_counts, sequence_duration, sleep_duration AS FLOAT
DIM trigger_duration, delay AS FLOAT
DIM Data_1[1000] AS LONG
DIM Data_2[1000] AS LONG

init:
  Cnt_Enable(0)
  Cnt_Mode(1,8)   ' Counter 1 set to increasing
  Par_7 = 0       ' acquisition done flag
  Par_8 = 0       ' repetition_counter
  number_of_signal_events = Par_5 * Par_6
  trigger_duration = 12  ' 120ns trigger pulse width (in 10 ns)
  Cnt_Clear(1)          ' Clear counter 1
  iteration_number = 0
  ' NOTE: The offsets (10 and 30) are historical calibration values
  ' that were determined empirically. The actual timing values are:
  ' count_time = (Par_3-10)/10  where Par_3 is passed from Python
  ' These offsets ensure proper timing calibration for the hardware setup.
  count_time = 30
  sequence_duration = 1550 ' since Par_9 is given in ns and IO_Sleep accepts params in 10ns, we divide by 10
  sleep_duration = sequence_duration - 200
  'sleep_duration = 1500323
  Conf_DIO(1100b) ' configure 0 - 15 as DIGIN, and 16 - 31 as DIGOUT
  ' Set digital output 21 to low (no trigger)
  DIGOUT(21, 0)
  DIGOUT(16, 0)
  ref_counts = 0
  sig_counts= 0
  delay = (sequence_duration + 18 + 12) * 3 ' * 10 since the variables are in 10 ns and /(10/3) as the value has to be in number or clock ticks which is 10/3 for T11 processor
  Processdelay = delay
  i = 0
  DO
    Data_1[i] = 0 '20 data points
    Data_2[i] = 0 '20 data points
    i = i +1
  UNTIL (i = 1000)
event:
  iteration_number = iteration_number + 1 ' Since Data_1 and Data_2 start at index 1
  Par_8 = Par_8 + 1          ' current event number (increase for signal count)
  DIGOUT(21, 1)              ' Set trigger high
  DIGOUT(28, 1)
  IO_Sleep(trigger_duration)
  DIGOUT(21, 0)              ' Set trigger low
  DIGOUT(28, 0)
  Cnt_Enable(1)          ' enable counter 1
  IO_Sleep(1200)
  DIGOUT(16, 1)
  IO_Sleep(140)  
  Cnt_Clear(1)           ' Clear counter 
  IO_Sleep(count_time)          ' count time 300 ns
  sig_counts = Cnt_Read(1)
  IO_Sleep(8)
  Cnt_Clear(1)
  IO_Sleep(count_time)          ' count time 300 ns
  ref_counts = Cnt_Read(1)        ' accumulate ref
  DIGOUT(16, 0)
  Cnt_Enable(0)          ' disable counter 1
  Data_1[iteration_number] = Data_1[iteration_number] + sig_counts
  Data_2[iteration_number] = Data_2[iteration_number] + ref_counts        ' accumulate ref
  ref_counts = 0
  sig_counts = 0
  IF (iteration_number = Par_6) THEN 'if we did all of our iterations for a given sequence, then go back to iteration 0
    iteration_number = 0
  ENDIF
  ' Check if we've completed all repetitions and if iteration_number is 0 which means that it got to Par_6
  ' Par_5 contains the number of repetitions per scan point (e.g., 50000)
  IF (Par_8 = 1000000) THEN '(Par_8 = number_of_signal_events) THEN
    Par_7=1
    Cnt_Enable(0)
    DIGOUT(21, 0)                  ' Ensure trigger is low
    END
  ENDIF
