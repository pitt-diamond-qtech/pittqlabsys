'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 1000000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = PittQLabSys
'<Header End>
'
' ODMR Sweep Counter Script for Enhanced ODMR Experiments
' This script generates a voltage ramp on AO1 for SG384 modulation input
' and counts photons synchronously during the sweep.
'
' SG384 FM Input Specifications:
' - Voltage Range: ±1V for ± full deviation
' - Input Impedance: 100 kΩ
' - Input Coupling: AC (4 Hz high pass) or DC
' - Modulation Bandwidth: >100 kHz
' - Connector: Rear-panel BNC
'
' Parameters:
' Par_1  - Counter value (read)
' Par_2  - Integration time per step in microseconds (set by experiment)
' Par_3  - Number of steps in sweep (set by experiment)
' Par_4  - Current step index (0 to num_steps-1)
' Par_5  - Sweep direction (0=forward, 1=reverse)
' Par_6  - Current voltage output (-1.0 to +1.0)
' Par_7  - Sweep complete flag (0=in progress, 1=complete)
' Par_8  - Total counts for current step
' Par_9  - Reserved for future use
' Par_10 - Reserved for future use
'
' Analog Outputs:
' AO1 - Voltage ramp for SG384 FM input (-1V to +1V)
' AO2 - Reserved for future use

#Include ADwinGoldII.inc

DIM step_index AS LONG
DIM step_count AS LONG
DIM integration_cycles AS LONG
DIM voltage_step AS FLOAT
DIM current_voltage AS FLOAT
DIM sweep_direction AS LONG
DIM sweep_complete AS LONG

init:
  ' Initialize counter
  Cnt_Enable(0)   ' Disable counter
  Cnt_Clear(1)    ' Clear counter 1
  Cnt_Mode(1,8)   ' Set counter 1 to increment on falling edge
  Cnt_Enable(1)   ' Enable counter 1
  
  ' Initialize analog outputs
  AO_Config(1, 0, 0, 1)  ' Configure AO1 for ±1V range (SG384 FM input)
  AO_Config(2, 0, 0, 0)  ' Configure AO2 for ±10V range
  
  ' Initialize variables
  step_index = 0
  step_count = 0
  integration_cycles = 0
  sweep_direction = 0  ' Start with forward sweep
  sweep_complete = 0
  
  ' Calculate voltage step size
  ' Voltage goes from -1V to +1V over num_steps
  voltage_step = 2.0 / Par_3  ' 2V range divided by number of steps
  
  ' Start at -1V
  current_voltage = -1.0
  AO_Write(1, current_voltage)
  
  ' Reset sweep complete flag
  Par_7 = 0

Event:
  ' Read counter value
  Par_1 = Cnt_Read(1)
  
  ' Accumulate counts for current step
  Par_8 = Par_8 + Par_1
  
  ' Clear counter for next cycle
  Cnt_Clear(1)
  
  ' Check if we've completed the integration time for this step
  integration_cycles = integration_cycles + 1
  IF (integration_cycles >= Par_2) THEN
    ' Integration time complete for this step
    ' Move to next step
    Inc(step_index)
    Par_4 = step_index
    
    ' Check if we've completed all steps
    IF (step_index >= Par_3) THEN
      ' Sweep complete
      sweep_complete = 1
      Par_7 = 1
      
      ' Reset for next sweep
      step_index = 0
      Par_4 = 0
      
      ' Toggle sweep direction for next sweep (if needed)
      IF (Par_5 = 1) THEN
        sweep_direction = 1 - sweep_direction  ' Toggle direction
      ENDIF
      
      ' Set voltage based on direction
      IF (sweep_direction = 0) THEN
        ' Forward sweep: start at -1V
        current_voltage = -1.0
      ELSE
        ' Reverse sweep: start at +1V
        current_voltage = 1.0
        voltage_step = -voltage_step  ' Negative step for reverse sweep
      ENDIF
      
      ' Reset voltage step for next sweep
      IF (sweep_direction = 0) THEN
        voltage_step = 2.0 / Par_3
      ELSE
        voltage_step = -2.0 / Par_3
      ENDIF
      
    ELSE
      ' Move to next voltage step
      current_voltage = current_voltage + voltage_step
      
      ' Ensure voltage stays within bounds
      IF (current_voltage > 1.0) THEN
        current_voltage = 1.0
      ENDIF
      IF (current_voltage < -1.0) THEN
        current_voltage = -1.0
      ENDIF
    ENDIF
    
    ' Output current voltage
    AO_Write(1, current_voltage)
    Par_6 = current_voltage
    
    ' Reset integration cycle counter
    integration_cycles = 0
  ENDIF

Finish:
  ' Cleanup
  Cnt_Enable(0)  ' Disable counter
  AO_Write(1, 0.0)  ' Set FM output to 0V 