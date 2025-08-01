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
' Parameters:
' Par_1  - Counter value (read)
' Par_2  - Integration time per step in microseconds (set by experiment)
' Par_3  - Number of steps in sweep (set by experiment)
' Par_4  - Current step index (0 to num_steps-1)
' Par_5  - Sweep direction (0=forward, 1=reverse)
' Par_6  - Current voltage output (-1.0 to +1.0)
' Par_7  - Sweep complete flag (0=in progress, 1=complete)
' Par_8  - Total counts for current step
' Par_9  - Sweep cycle counter (0=forward, 1=reverse, 2=complete)
' Par_10 - Data ready flag (0=collecting, 1=ready to read)
'
' Data Arrays:
' Data_1 - Forward sweep counts (index 0 to num_steps-1)
' Data_2 - Reverse sweep counts (index 0 to num_steps-1)
' Data_3 - Forward sweep voltages (index 0 to num_steps-1)
' Data_4 - Reverse sweep voltages (index 0 to num_steps-1)
'
' Analog Outputs:
' AO1 - Voltage ramp for SG384 FM input (-1V to +1V)

#Include ADwinGoldII.inc

DIM step_index AS LONG
DIM integration_cycles AS LONG
DIM voltage_step AS FLOAT
DIM current_voltage AS FLOAT
DIM total_counts AS LONG
DIM sweep_direction AS LONG
DIM sweep_cycle AS LONG
DIM data_ready AS LONG

init:
  ' Initialize counter
  Cnt_Enable(0)   ' Disable counter
  Cnt_Clear(1)    ' Clear counter 1
  Cnt_Mode(1,8)   ' Set counter 1 to increment on falling edge
  Cnt_Enable(1)   ' Enable counter 1
  
  ' Initialize analog outputs
  AO_Config(1, 0, 0, 1)  ' Configure AO1 for ±1V range (SG384 FM input)
  
  ' Initialize variables
  step_index = 0
  integration_cycles = 0
  total_counts = 0
  sweep_direction = 0  ' Start with forward sweep
  sweep_cycle = 0
  data_ready = 0
  
  ' Calculate voltage step size
  IF (Par_3 > 0) THEN
    voltage_step = 2.0 / Par_3  ' 2V range divided by number of steps
  ELSE
    voltage_step = 0.02  ' Default step size
  ENDIF
  
  ' Start at -1V for forward sweep
  current_voltage = -1.0
  AO_Write(1, current_voltage)
  
  ' Reset parameters
  Par_4 = 0
  Par_5 = 0  ' Forward sweep
  Par_6 = current_voltage
  Par_7 = 0  ' Sweep not complete
  Par_8 = 0
  Par_9 = 0  ' Forward sweep cycle
  Par_10 = 0 ' Data not ready
  
  ' Clear data arrays
  Data_Clear(1, 0, Par_3 - 1)  ' Clear forward counts
  Data_Clear(2, 0, Par_3 - 1)  ' Clear reverse counts
  Data_Clear(3, 0, Par_3 - 1)  ' Clear forward voltages
  Data_Clear(4, 0, Par_3 - 1)  ' Clear reverse voltages

Event:
  ' Read counter value
  Par_1 = Cnt_Read(1)
  
  ' Accumulate counts for current step
  total_counts = total_counts + Par_1
  Par_8 = total_counts
  
  ' Clear counter for next cycle
  Cnt_Clear(1)
  
  ' Check if we've completed the integration time for this step
  integration_cycles = integration_cycles + 1
  IF (integration_cycles >= Par_2) THEN
    ' Integration time complete for this step
    ' Store data in appropriate array based on sweep direction
    IF (sweep_direction = 0) THEN
      ' Forward sweep: store in Data_1 (counts) and Data_3 (voltages)
      Data_1(step_index) = total_counts
      Data_3(step_index) = current_voltage
    ELSE
      ' Reverse sweep: store in Data_2 (counts) and Data_4 (voltages)
      Data_2(step_index) = total_counts
      Data_4(step_index) = current_voltage
    ENDIF
    
    ' Move to next step
    step_index = step_index + 1
    Par_4 = step_index
    
    ' Check if we've completed all steps for current direction
    IF (step_index >= Par_3) THEN
      ' Current direction complete
      IF (sweep_direction = 0) THEN
        ' Forward sweep complete, start reverse sweep
        sweep_direction = 1
        sweep_cycle = 1
        step_index = 0
        Par_4 = 0
        Par_5 = 1  ' Reverse sweep
        
        ' Start reverse sweep from +1V
        current_voltage = 1.0
        voltage_step = -2.0 / Par_3  ' Negative step for reverse sweep
        
      ELSE
        ' Reverse sweep complete, both sweeps done
        sweep_cycle = 2
        Par_7 = 1  ' Sweep complete
        Par_9 = 2  ' Complete cycle
        Par_10 = 1 ' Data ready to read
        
        ' Reset for next cycle
        step_index = 0
        Par_4 = 0
        sweep_direction = 0
        sweep_cycle = 0
        data_ready = 0
        current_voltage = -1.0
        voltage_step = 2.0 / Par_3
      ENDIF
      
    ELSE
      ' Move to next voltage step in current direction
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
    
    ' Reset integration cycle counter and counts
    integration_cycles = 0
    total_counts = 0
    Par_8 = 0
  ENDIF

Finish:
  ' Cleanup
  Cnt_Enable(0)  ' Disable counter
  AO_Write(1, 0.0)  ' Set FM output to 0V 