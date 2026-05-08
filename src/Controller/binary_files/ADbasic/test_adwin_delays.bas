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
' This process generates digout signals to test the time it takes for each process used in adwin_triggering_proteus.bas to optimize adwin's time delays for pulsed ODMR experiments
' for testing the ADwin -> proteus control architecture.
'
' Hardware Setup:
' - Test 1: ADwin Digital Output -> OSCILLOSCOPE: testing the digout
' - Test 2: ADwin Digital Output -> Proteus TRIG 1 IN (front panel): testing digout and proteus triggering delay
' digout, Cnt_Enable(1), digout
' digout, Cnt_Enable(0), digout
' digout 1, digout 2
' digout, CPU_Sleep, digout
' digout, CPU_Sleep, digout
' digout, Cnt_Read(1), digout
' digout, Cnt_Clear(1), digout

#Include ADwinGoldII.inc
DIM count_time AS FLOAT
'DIM trigger_duration AS FLOAT
  
  
' test 3
'DIGOUT(21, 1)
'Cnt_enable(0)
'DIGOUT(16, 1)
'CPU_Sleep(count_time)
'DIGOUT(21, 0)
'DIGOUT(16, 0)
'CPU_Sleep(count_time)
'Cnt_enable(1)

' test 4
'DIGOUT(21, 1)
'CPU_Sleep(count_time)
'DIGOUT(16, 1)
'DIGOUT(21, 0)
'DIGOUT(16, 0)

' test 5
'DIGOUT(21, 1)
'Cnt_read(1)
'DIGOUT(16, 1)
'DIGOUT(21, 0)
'DIGOUT(16, 0)

'test 6
'DIGOUT(21, 1)
'Cnt_Clear(1)
'DIGOUT(16, 1)
'DIGOUT(21, 0)
'DIGOUT(16, 0)

init:
  Cnt_Enable(0)
  Cnt_Mode(1,8)   ' Counter 1 set to increasing
  'trigger_duration = 1  ' 10ns trigger pulse width (in 10 ns)

  Cnt_Clear(1)          ' Clear counter 1
  count_time = 60 ' 600/10 as it's 600 ns but units are in 10 ns
  Conf_DIO(1100b) ' configure 0 - 15 as DIGIN, and 16 - 31 as DIGOUT
  ' Set digital output 21 to low (no trigger)
  DIGOUT(21, 0)
  DIGOUT(16, 0)
  Processdelay = 2*count_time*3
event:
  DIGOUT(28, 1)
  DIGOUT(16, 1)
  CPU_Sleep(count_time)
  DIGOUT(28, 0)
  DIGOUT(16, 0)
