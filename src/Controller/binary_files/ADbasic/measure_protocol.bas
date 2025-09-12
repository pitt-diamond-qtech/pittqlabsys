<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 2
' Initial_Processdelay           = 3000
' Eventsource                    = External
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Duttlab
<Header End>
' MeasureProtocol.bas
' Configured as Process 2, Priority High, External trigger.
' This process handles photon counting for ODMR pulsed experiments.
' AWG520 triggers this process via external event, and we perform
' dual-gate counting to separate signal from reference.


#Include ADwinGoldII.inc
DIM signal_count, reference_count, repetition_counter AS LONG
DIM count_time, reset_time as LONG


init:
  Cnt_Enable(0)
  Cnt_Mode(1,8)          ' Counter 1 set to increasing
  
  Cnt_Clear(1)           ' Clear counter 1
  repetition_counter=0
  signal_count=0
  reference_count=0
  Par_10=0

  ' NOTE: The offsets (10 and 30) are historical calibration values
  ' that were determined empirically. The actual timing values are:
  ' count_time = (Par_3-10)/10  where Par_3 is passed from Python
  ' reset_time = (Par_4-30)/10  where Par_4 is passed from Python
  ' These offsets ensure proper timing calibration for the hardware setup.
  count_time = (Par_3-10)/10 'added on 2/6/20 to allow passing parameter from Python
  reset_time = (Par_4-30)/10  'added on 2/6/20 to allow passing parameter from Python


event:
  Inc(repetition_counter)
  Cnt_Enable(1)          ' enable counter 1
  CPU_Sleep(count_time)          ' count time 300 ns
  Cnt_Enable(0)          ' disable counter 1
  Cnt_Latch(1)           ' Latch counter 1
  CPU_Sleep(reset_time)         ' reset time 2000 ns
  Cnt_Enable(1)          ' enable counter 1
  CPU_Sleep(count_time)          ' count time 300 ns
  Cnt_Enable(0)          ' disable counter 1
  signal_count=signal_count+Cnt_Read_Latch(1)  ' accumulate signal counts
  reference_count=reference_count+Cnt_Read(1)        ' accumulate total counts (signal + reference)
  Cnt_Clear(1)           ' Clear counter 1
  

  ' Check if we've completed all repetitions for the current scan point
  ' Par_5 contains the number of repetitions per scan point (e.g., 50000)
  IF (repetition_counter>=Par_5) THEN
    ' Store accumulated counts in ADwin parameters for Python to read
    Par_1=signal_count        ' Signal counts for this scan point
    Par_2=reference_count-signal_count  ' Reference counts (total - signal) for this scan point
    
    ' Reset counters for next scan point
    signal_count=0
    reference_count=0
    repetition_counter=0
    
    ' Increment scan point counter (Par_10 tracks which scan point we're on)
    Inc(Par_10)
  ENDIF


finish:
  Cnt_Enable(0)
