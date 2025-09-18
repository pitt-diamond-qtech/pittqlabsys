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
' Info_Last_Save                 = DUTTLAB8  Duttlab8\Duttlab
'<Header End>
'
' ODMR Sweep Counter Script - DEBUG VERSION
' This script helps diagnose counting issues by providing detailed diagnostics
'
' Parameters:
' Par_1  - Raw counter value (read every cycle)
' Par_2  - Integration time per step in microseconds (set by experiment)
' Par_3  - Number of steps in sweep (set by experiment)
' Par_4  - Current step index (0 to num_steps-1)
' Par_5  - Sweep direction (0=forward, 1=reverse)
' Par_6  - Current voltage output (-1.0 to +1.0)
' Par_7  - Sweep complete flag (0=in progress, 1=complete)
' Par_8  - Total counts for current step
' Par_9  - Sweep cycle counter (0=forward, 1=reverse, 2=complete)
' Par_10 - Data ready flag (0=collecting, 1=ready to read)
' Par_11 - Settle time after voltage step in microseconds
' Par_12 - DEBUG: Event cycle counter
' Par_13 - DEBUG: Integration cycle counter
' Par_14 - DEBUG: Raw counter before clear
' Par_15 - DEBUG: Counter mode (0=rising, 8=falling)
' Par_16 - DEBUG: Total captured steps

#Include ADwinGoldII.inc

DIM step_index AS LONG
DIM integration_cycles AS LONG
DIM settle_cycles AS LONG
DIM voltage_step AS FLOAT
DIM current_voltage AS FLOAT
DIM total_counts AS LONG
DIM sweep_direction AS LONG
DIM sweep_cycle AS LONG
DIM data_ready AS LONG
DIM dac_value AS LONG
DIM event_cycle AS LONG
DIM raw_counter AS LONG
DIM capture_index AS LONG  ' DEBUG: Index for capturing step data

' Declare data arrays for storing sweep data
DIM Data_1[10000] AS LONG  ' Forward sweep counts
DIM Data_2[10000] AS LONG  ' Reverse sweep counts  
DIM Data_3[10000] AS FLOAT ' Forward sweep voltages
DIM Data_4[10000] AS FLOAT ' Reverse sweep voltages

' DEBUG: Additional arrays to capture step progression
DIM Data_5[10000] AS LONG  ' Step indices captured during sweep
DIM Data_6[10000] AS LONG  ' Sweep directions captured during sweep
DIM Data_7[10000] AS LONG  ' Integration cycles captured during sweep
DIM Data_8[10000] AS LONG  ' Event cycles captured during sweep

init:
  ' Initialize counter
  Cnt_Enable(0)   ' Disable counter
  Cnt_Clear(1)    ' Clear counter 1
  Cnt_Mode(1,8)   ' DEBUG: Use falling edge (mode 8) - same as other working scripts
  Cnt_Enable(1)   ' Enable counter 1
  
  ' Initialize DAC for ±10V range (but we'll clamp output to ±1V for SG384)
  DAC(1, 1)       ' Enable DAC1
  Start_DAC(1)    ' Start DAC1 output
  
  ' Initialize variables
  step_index = 0
  integration_cycles = 0
  settle_cycles = 0
  total_counts = 0
  sweep_direction = 0  ' Start with forward sweep
  sweep_cycle = 0
  data_ready = 0
  event_cycle = 0
  capture_index = 0  ' DEBUG: Initialize capture index
  
  ' Calculate voltage step size for ±1V range (SG384 safe)
  IF (Par_3 > 0) THEN
    voltage_step = 2.0 / Par_3  ' 2V range divided by number of steps
  ELSE
    voltage_step = 0.02  ' Default step size
  ENDIF
  
  ' Start at -1V for forward sweep (SG384 safe)
  current_voltage = -1.0
  ' Convert voltage to DAC value: (voltage + 10) * 65535 / 20
  dac_value = (current_voltage + 10.0) * 65535 / 20
  Write_DAC(1, dac_value)
  
  ' Start settle time after initial voltage
  settle_cycles = Par_11  ' Settle time in microseconds
  
  ' Reset parameters
  Par_4 = 0
  Par_5 = 0  ' Forward sweep
  Par_6 = current_voltage
  Par_7 = 0  ' Sweep not complete
  Par_8 = 0
  Par_9 = 0  ' Forward sweep cycle
  Par_10 = 0 ' Data not ready
  Par_12 = 0 ' Event cycle counter
  Par_13 = 0 ' Integration cycle counter
  Par_14 = 0 ' Raw counter before clear
  Par_15 = 0 ' Counter mode (0=rising)
  Par_16 = 0 ' DEBUG: Total captured steps
  
  ' Clear data arrays by setting all elements to 0
  FOR step_index = 0 TO Par_3 - 1
    Data_1[step_index] = 0  ' Clear forward counts
    Data_2[step_index] = 0  ' Clear reverse counts
    Data_3[step_index] = 0  ' Clear forward voltages
    Data_4[step_index] = 0  ' Clear reverse voltages
  NEXT step_index
  
  ' DEBUG: Clear debug capture arrays
  FOR step_index = 0 TO 9999
    Data_5[step_index] = 0  ' Clear step indices
    Data_6[step_index] = 0  ' Clear sweep directions
    Data_7[step_index] = 0  ' Clear integration cycles
    Data_8[step_index] = 0  ' Clear event cycles
  NEXT step_index

Event:
  ' Increment event cycle counter
  event_cycle = event_cycle + 1
  Par_12 = event_cycle
  
  ' Read raw counter value
  raw_counter = Cnt_Read(1)
  Par_1 = raw_counter
  Par_14 = raw_counter  ' Store raw counter before any clearing
  
  ' Check if we're in settle time or integration time
  IF (settle_cycles > 0) THEN
    ' In settle time - just wait
    settle_cycles = settle_cycles - 1
  ELSE
    ' In integration time - accumulate counts
    total_counts = total_counts + raw_counter
    Par_8 = total_counts
    
    ' DEBUG: Only clear counter at the END of integration period
    ' (This is the key fix - don't clear every cycle!)
    
    ' Check if we've completed the integration time for this step
    integration_cycles = integration_cycles + 1
    Par_13 = integration_cycles
    
    IF (integration_cycles >= Par_2) THEN
      ' Integration time complete for this step
      ' NOW clear the counter for next step
      Cnt_Clear(1)
      
      ' Store data in appropriate array based on sweep direction
      IF (sweep_direction = 0) THEN
        ' Forward sweep: store in Data_1 (counts) and Data_3 (voltages)
        Data_1[step_index] = total_counts
        Data_3[step_index] = current_voltage
      ELSE
        ' Reverse sweep: store in Data_2 (counts) and Data_4 (voltages)
        Data_2[step_index] = total_counts
        Data_4[step_index] = current_voltage
      ENDIF
      
      ' DEBUG: Capture step data for analysis
      Data_5[capture_index] = step_index
      Data_6[capture_index] = sweep_direction
      Data_7[capture_index] = integration_cycles
      Data_8[capture_index] = event_cycle
      capture_index = capture_index + 1
      
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
          step_index = 0  ' FIXED: Start reverse from first step (0)
          Par_4 = step_index
          Par_5 = 1  ' Reverse sweep
          
          ' Start reverse sweep from +1V (SG384 safe)
          current_voltage = 1.0
          voltage_step = -2.0 / Par_3  ' Negative step for reverse sweep
          
        ELSE
          ' Reverse sweep complete, both sweeps done
          sweep_cycle = 2
          Par_7 = 1  ' Sweep complete
          Par_9 = 2  ' Complete cycle
          Par_10 = 1 ' Data ready to read
          Par_16 = capture_index  ' DEBUG: Store total captured steps
          
          ' Reset for next cycle
          step_index = 0
          Par_4 = 0
          sweep_direction = 0
          sweep_cycle = 0
          data_ready = 0
          current_voltage = -1.0
          voltage_step = 2.0 / Par_3
          capture_index = 0  ' DEBUG: Reset capture index for next cycle
        ENDIF
        
      ELSE
        ' Move to next voltage step in current direction
        IF (sweep_direction = 0) THEN
          ' Forward sweep: increment voltage
          current_voltage = current_voltage + voltage_step
        ELSE
          ' Reverse sweep: decrement voltage
          current_voltage = current_voltage + voltage_step
        ENDIF
        
        ' CRITICAL: Clamp voltage to ±1V for SG384 safety
        IF (current_voltage > 1.0) THEN
          current_voltage = 1.0
        ENDIF
        IF (current_voltage < -1.0) THEN
          current_voltage = -1.0
        ENDIF
      ENDIF
      
      ' Output current voltage using DAC (clamped to ±1V for SG384)
      ' Convert voltage to DAC value: (voltage + 10) * 65535 / 20
      dac_value = (current_voltage + 10.0) * 65535 / 20
      ' Ensure DAC value is within valid range
      IF (dac_value < 0) THEN
        dac_value = 0
      ENDIF
      IF (dac_value > 65535) THEN
        dac_value = 65535
      ENDIF
      Write_DAC(1, dac_value)
      Par_6 = current_voltage
      
      ' Start settle time after voltage change
      settle_cycles = Par_11  ' Settle time in microseconds
      
      ' Reset integration cycle counter and counts
      integration_cycles = 0
      total_counts = 0
      Par_8 = 0
    ENDIF
  ENDIF

Finish:
  ' Cleanup
  Cnt_Enable(0)  ' Disable counter
  ' Set DAC output to 0V (center of range, SG384 safe)
  Write_DAC(1, 32768)
