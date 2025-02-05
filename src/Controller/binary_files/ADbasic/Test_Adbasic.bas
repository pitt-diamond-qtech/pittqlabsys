'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 4
' Initial_Processdelay           = 3000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = Low
' Priority_Low_Level             = 1
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Duttlab
'<Header End>
'This script serves to test the adwin.py controller
'It sets some variables which are then read
'Set to run on processor 4

#Include ADwinGoldII.inc

Dim Data_56[5] as LONG  'array_56 with integer values of length 6
Dim Data_8[5] as STRING 'array_8 as string of length 5
Dim index as LONG       'int variable (note: this can't be read by python controller)

Init:
  FPar_12 = 5.0     'sets flaot_variable_12 to 5.0
  Data_8 = "Hello"  'sets array_8 to "Hello"
  
  index = 1         'array index starts at 1 in ADbaisc
  Par_1 = 1

Event:
  'DO                'Sets index value = index number for 1,2,3,4,5
    '  Data_56[index] = index
    '  Inc(index)      'Increments index by 1
    'UNTIL (index = 6)
  IF (index < 6) THEN
    Data_56[index] = index
  ENDIF
  Inc(index)



