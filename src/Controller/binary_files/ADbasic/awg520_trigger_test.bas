<ADbasic Header, Headerversion 001.001>
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
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Duttlab
<Header End>
' AWG520_Trigger_Test.bas
' This process generates trigger pulses to control AWG520 external triggering
' for testing the ADwin→AWG520 control architecture.
'
' Hardware Setup:
' - ADwin Digital Output → AWG520 TRIG IN (rear panel)
' - AWG520 configured for external trigger with Wait Trigger enabled
' - Computer controls JUMP_MODE software for sequence advancement
'
' Operation:
' - Process generates trigger pulses at specified intervals
' - Each trigger causes AWG520 to advance to next sequence line
' - Computer can control timing and number of triggers via parameters


#Include ADwinGoldII.inc
DIM trigger_counter AS LONG
DIM trigger_interval AS LONG
DIM max_triggers AS LONG
DIM trigger_duration AS LONG
DIM current_state AS LONG


init:
  ' Initialize variables
  trigger_counter = 0
  trigger_interval = 1000000    ' 1 second default (in microseconds)
  max_triggers = 10             ' Default 10 triggers
  trigger_duration = 1000       ' 1ms trigger pulse width
  current_state = 0             ' 0=idle, 1=trigger_high, 2=trigger_low
  
  ' Set digital output to low (no trigger)
  DIGOUT(0, 0)
  
  ' Set parameters for Python control
  Par_1 = trigger_counter       ' Current trigger count
  Par_2 = trigger_interval      ' Trigger interval in microseconds
  Par_3 = max_triggers          ' Maximum number of triggers
  Par_4 = trigger_duration      ' Trigger pulse duration in microseconds
  Par_5 = current_state         ' Current state (0=idle, 1=high, 2=low)


event:
  ' Main trigger generation loop
  IF current_state = 0 THEN
    ' Idle state - check if we should generate a trigger
    IF trigger_counter < max_triggers THEN
      ' Start trigger pulse
      DIGOUT(0, 1)              ' Set trigger high
      current_state = 1
      Par_5 = current_state
    ELSE
      ' All triggers completed
      GOTO finish
    ENDIF
    
  ELSEIF current_state = 1 THEN
    ' Trigger high state - wait for pulse duration
    CPU_Sleep(trigger_duration)
    DIGOUT(0, 0)                ' Set trigger low
    current_state = 2
    Par_5 = current_state
    
  ELSEIF current_state = 2 THEN
    ' Trigger low state - wait for interval before next trigger
    CPU_Sleep(trigger_interval - trigger_duration)
    trigger_counter = trigger_counter + 1
    Par_1 = trigger_counter
    current_state = 0            ' Back to idle
    Par_5 = current_state
  ENDIF


finish:
  ' Clean up
  DIGOUT(0, 0)                  ' Ensure trigger is low
  current_state = 0
  Par_5 = current_state
