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
#INCLUDE ADwinGoldII.inc
Dim i As Long
Init:
  Processdelay = 10000
  i = 1
  Write_DAC(1, 34432) '34432

Event:
  Start_DAC()
  Write_DAC(1, 33010) '34432 high 33010 low
  IO_Sleep(500)
  Write_DAC(1, 34432) '34432
