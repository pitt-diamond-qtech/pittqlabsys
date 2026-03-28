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
' Par_3: count_time (with calibration offset)
' Par_4: reset_time (with calibration offset): time between signal counts and reference counts
' Par_5: repeat_count
' Par_6: number of iterations
' Par_7: acquisition done flag
' Par_8: repetition_counter
' Data_1: signal counts
' Data_2: reference counts
' Par_9: sequence_duration (with calibration offset): Time of the awg sequence
' Par_10: proteus response delay

#Include ADwinGoldII.inc
DIM signal_count, ref_count, number_of_signal_events AS LONG
DIM iteration_number, i as LONG
DIM count_time, reset_time, sequence_duration, sleep_duration AS FLOAT
DIM trigger_duration, delay, proteus_response AS FLOAT
DIM Data_1[20] AS LONG ' 100000 is the maximum number of iterations
DIM Data_2[20] AS LONG ' 100000 is the maximum number of iterations

init:
  Cnt_Enable(0)
  Cnt_Mode(1,8)   ' Counter 1 set to increasing
  Par_7 = 0       ' acquisition done flag
  Par_8 = 0       ' repetition_counter
  number_of_signal_events = Par_5 * Par_6
  trigger_duration = 1  ' 10ns trigger pulse width (in 10 ns)

  Cnt_Clear(1)          ' Clear counter 1
  signal_count=0
  ref_count=0
  iteration_number = 0
  ' NOTE: The offsets (10 and 30) are historical calibration values
  ' that were determined empirically. The actual timing values are:
  ' count_time = (Par_3-10)/10  where Par_3 is passed from Python
  ' reset_time = (Par_4-30)/10  where Par_4 is passed from Python
  ' These offsets ensure proper timing calibration for the hardware setup.
  count_time = (Par_3-10)/10 'added on 2/6/20 to allow passing parameter from Python
  reset_time = (Par_4-30)/10  'added on 2/6/20 to allow passing parameter from Python
  sequence_duration = Par_9/10 ' since Par_9 is given in ns and CPU_Sleep accepts params in 10ns, we divide by 10
  proteus_response = Par_10/10
  'old
  'sleep_duration = sequence_duration + proteus_response - trigger_duration 
  'new
  sleep_duration = sequence_duration + proteus_response - trigger_duration - count_time*2 - reset_time
  Conf_DIO(1100b) ' configure 0 - 15 as DIGIN, and 16 - 31 as DIGOUT
  ' Set digital output 21 to low (no trigger)
  DIGOUT(21, 0)
  DIGOUT(16, 0)
  'old
  'delay = (sequence_duration + proteus_response+ count_time + reset_time + count_time + 10) * 3 ' * 10 since the variables are in 10 ns and /(10/3) as the value has to be in number or clock ticks which is 10/3 for T11 processor
  delay = (sequence_duration + proteus_response + 10) * 3
  Processdelay = delay
  i = 1
  DO
    Data_1[i] = 0
    Data_2[i] = 0
    i = i +1
  UNTIL (i = 21)
  Write_DAC(1, 33010)
event:
  Cnt_Enable(0)
  Cnt_Clear(1)
  Par_8 = Par_8 + 1          ' current event number (increase for signal count)
  iteration_number = iteration_number + 1 ' Since Data_1 and Data_2 start at index 1
  DIGOUT(21, 1)              ' Set trigger high
  Write_DAC(1, 34880)
  Start_DAC()
  CPU_Sleep(trigger_duration)
  DIGOUT(21, 0)              ' Set trigger low
  CPU_Sleep(sleep_duration)
  Cnt_Enable(1)            ' enable counter 1
  DIGOUT(16, 1)
  CPU_Sleep(count_time)      ' count time 300 ns
  Cnt_Enable(0)            ' disable counter 1
  DIGOUT(16, 0)
  signal_count=Cnt_Read(1)    ' accumulate signal counts
  Cnt_Clear(1)
  Data_1[iteration_number] = Data_1[iteration_number] + signal_count
  CPU_Sleep(reset_time)
  Cnt_Enable(1)              ' enable counter 1
  DIGOUT(16, 1)
  CPU_Sleep(count_time)  ' count time 300 ns
  Cnt_Enable(0)        ' disable counter 1
  DIGOUT(16, 0)
  ref_count=Cnt_Read(1)         ' accumulate reference counts
  Cnt_Clear(1)             ' Clear counter 1
  Data_2[iteration_number] = Data_2[iteration_number] + ref_count
  signal_count = 0
  ref_count = 0
  Write_DAC(1, 33010)
  IF (iteration_number = Par_6) THEN 'if we did all of our iterations for a given sequence, then go back to iteration 0
    iteration_number = 0
  ENDIF
  ' Check if we've completed all repetitions and if iteration_number is 0 which means that it got to Par_6
  ' Par_5 contains the number of repetitions per scan point (e.g., 50000)
  IF (Par_8 = number_of_signal_events) THEN
    Par_7=1
    Cnt_Enable(0)
    DIGOUT(21, 0)                  ' Ensure trigger is low
    END
  ENDIF
