'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 2
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
' ODMR Counter Script with FM Modulation
' This script enables counting on counter 1 for ODMR experiments with optional laser power tracking
' and analog output control for FM modulation of the SG384 microwave generator.
'
' SG384 FM Input Specifications:
' - Voltage Range: ±1V for ± full deviation
' - Input Impedance: 100 kΩ
' - Input Coupling: AC (4 Hz high pass) or DC
' - Modulation Bandwidth: >100 kHz
' - Connector: Rear-panel BNC
'
' IMPORTANT: Voltage is constrained to ±1V for SG384 compatibility
' DAC operates at ±10V range for precision, but output is clamped to ±1V
'
' Parameters:
' Par_1  - Counter value (read)
' Par_2  - Integration time in microseconds (set by experiment)
' Par_3  - Laser power analog input (read from ADC1, channel 1)
' Par_4  - Number of samples to average (set by experiment)
' Par_5  - Current sample index
' Par_6  - Summed counts for averaging
' Par_7  - Summed laser power for averaging
' Par_8  - Final averaged counts (output)
' Par_9  - Final averaged laser power (output)
' Par_10 - Enable laser power tracking (0=disabled, 1=enabled)
' Par_11 - Enable FM modulation (0=disabled, 1=enabled)
' Par_12 - FM modulation frequency in Hz (set by experiment)
' Par_13 - FM modulation amplitude in volts (0-1V for SG384, set by experiment)
' Par_14 - Current FM phase (internal)
' Par_15 - Current sweep step index (0 to num_steps-1)
' Par_16 - Number of sweep steps (set by experiment)
' Par_17 - Sweep direction (0=forward, 1=reverse)
' Par_18 - Current voltage output (-1.0 to +1.0, clamped for SG384)
' Par_19 - Sweep complete flag (0=in progress, 1=complete)
' Par_20 - Total counts for current step
'
' Data Arrays:
' Data_1 - Forward sweep counts (index 0 to num_steps-1)
' Data_2 - Reverse sweep counts (index 0 to num_steps-1)
' Data_3 - Forward sweep voltages (index 0 to num_steps-1)
' Data_4 - Reverse sweep voltages (index 0 to num_steps-1)
'
' DAC Outputs:
' DAC1 - FM modulation signal for SG384 (-1V to +1V, clamped for safety)
' DAC2 - Reserved for future use
'
' ADC Inputs:
' ADC1, Channel 1 - Laser power monitoring (0-10V range)

#Include ADwinGoldII.inc

DIM sample_index AS LONG
DIM integration_cycles AS LONG
DIM cycle_count AS LONG
DIM fm_phase AS FLOAT
DIM fm_step AS FLOAT
DIM fm_amplitude AS FLOAT
DIM fm_frequency AS FLOAT
DIM dac_value AS LONG
DIM adc_value AS LONG
DIM laser_voltage AS FLOAT
DIM step_index AS LONG
DIM voltage_step AS FLOAT
DIM current_voltage AS FLOAT
DIM total_counts AS LONG
DIM sweep_direction AS LONG
DIM sweep_cycle AS LONG
DIM data_ready AS LONG
DIM fm_signal AS FLOAT

DIM Data_1[10000] AS LONG  ' Forward sweep counts
DIM Data_2[10000] AS LONG  ' Reverse sweep counts  
DIM Data_3[10000] AS FLOAT ' Forward sweep voltages
DIM Data_4[10000] AS FLOAT ' Reverse sweep voltages

init:
  ' Initialize counter
  Cnt_Enable(0)   ' Disable counter
  Cnt_Clear(1)    ' Clear counter 1
  Cnt_Mode(1,8)   ' Set counter 1 to increment on falling edge
  Cnt_Enable(1)   ' Enable counter 1
  
  ' Initialize ADC for laser power tracking (ADC1, channel 1)
  ' Set multiplexer for ADC1 to channel 1 (001b = 1)
  Set_Mux1(001b)
  
  ' Initialize DAC for ±10V range (but we'll clamp output to ±1V for SG384)
  ' DAC values: 0 = -10V, 32768 = 0V, 65535 = +9.999695V
  DAC(1, 1)       ' Enable DAC1
  Start_DAC(1)    ' Start DAC1 output
  DAC(2, 1)       ' Enable DAC2
  Start_DAC(2)    ' Start DAC2 output
  
  ' Initialize variables
  sample_index = 1
  integration_cycles = 0
  cycle_count = 0
  fm_phase = 0.0
  fm_step = 0.0
  fm_amplitude = 0.0
  fm_frequency = 0.0
  step_index = 0
  voltage_step = 0.0
  current_voltage = -1.0
  total_counts = 0
  sweep_direction = 0
  sweep_cycle = 0
  data_ready = 0
  
  ' Calculate voltage step size for ±1V range (SG384 safe)
  IF (Par_16 > 0) THEN
    voltage_step = 2.0 / Par_16  ' 2V range divided by number of steps
  ELSE
    voltage_step = 0.02  ' Default step size
  ENDIF
  
  ' Reset averaging variables
  Par_6 = 0  ' Summed counts
  Par_7 = 0  ' Summed laser power
  
  ' Initialize FM modulation parameters
  IF (Par_11 = 1) THEN
    fm_frequency = Par_12  ' FM frequency in Hz
    fm_amplitude = Par_13  ' FM amplitude in volts
    ' Calculate phase step per cycle (assuming 1ms base delay)
    fm_step = 2.0 * 3.14159 * fm_frequency * 0.001  ' radians per ms
  ENDIF
  
  ' Reset parameters
  Par_15 = 0
  Par_17 = 0  ' Forward sweep
  Par_18 = current_voltage
  Par_19 = 0  ' Sweep not complete
  Par_20 = 0
  
  ' Clear data arrays by setting all elements to 0
  FOR step_index = 0 TO Par_16 - 1
    Data_1[step_index] = 0  ' Clear forward counts
    Data_2[step_index] = 0  ' Clear reverse counts
    Data_3[step_index] = 0  ' Clear forward voltages
    Data_4[step_index] = 0  ' Clear reverse voltages
  NEXT step_index

Event:
  ' Generate FM modulation signal if enabled
  IF (Par_11 = 1) THEN
    ' Calculate FM signal: amplitude * sin(2*pi*f*t)
    ' Constrain amplitude to ±1V for SG384 safety
    IF (fm_amplitude > 1.0) THEN
      fm_amplitude = 1.0
    ENDIF
    IF (fm_amplitude < -1.0) THEN
      fm_amplitude = -1.0
    ENDIF
    
    ' Calculate FM signal value
    fm_signal = fm_amplitude * SIN(fm_phase)
    
    ' Convert voltage to DAC value: (voltage + 10) * 65535 / 20
    dac_value = (fm_signal + 10.0) * 65535 / 20
    ' Ensure DAC value is within valid range
    IF (dac_value < 0) THEN
      dac_value = 0
    ENDIF
    IF (dac_value > 65535) THEN
      dac_value = 65535
    ENDIF
    
    ' Output FM signal using DAC
    Write_DAC(1, dac_value)
    
    fm_phase = fm_phase + fm_step
    ' Keep phase in reasonable range
    IF (fm_phase > 2.0 * 3.14159) THEN
      fm_phase = fm_phase - 2.0 * 3.14159
    ENDIF
    ' Store current phase for external monitoring
    Par_14 = fm_phase
  ELSE
    ' Set DAC1 to 0V when FM is disabled (center of range)
    Write_DAC(1, 32768)
  ENDIF
  
  ' Read counter value
  Par_1 = Cnt_Read(1)
  
  ' Read laser power if enabled
  IF (Par_10 = 1) THEN
    ' Start ADC conversion for ADC1
    Start_Conv(01b)  ' Start conversion for ADC1 only
    Wait_EOC(01b)    ' Wait for end of conversion
    
    ' Read ADC1 value (24-bit, 0-16777215 digits)
    adc_value = Read_ADC24(1)
    
    ' Convert ADC digits to voltage (0-10V range)
    ' ADC range: 0 digits = 0V, 16777215 digits = 10V
    laser_voltage = (adc_value * 10.0) / 16777215.0
    
    ' Store voltage value in parameter
    Par_3 = laser_voltage
  ELSE
    Par_3 = 0
  ENDIF
  
  ' Accumulate data for averaging
  Par_6 = Par_6 + Par_1  ' Add counts to sum
  IF (Par_10 = 1) THEN
    Par_7 = Par_7 + Par_3  ' Add laser power to sum
  ENDIF
  
  ' Clear counter for next cycle
  Cnt_Clear(1)
  
  ' Check if we've completed the integration time
  integration_cycles = integration_cycles + 1
  IF (integration_cycles >= Par_2) THEN
    ' Integration time complete, check if we need to average
    IF (sample_index >= Par_4) THEN
      ' Calculate averages
      Par_8 = Par_6 / Par_4  ' Average counts
      IF (Par_10 = 1) THEN
        Par_9 = Par_7 / Par_4  ' Average laser power
      ELSE
        Par_9 = 0
      ENDIF
      
      ' Store data in appropriate array based on sweep direction
      IF (step_index < Par_16) THEN
        IF (sweep_direction = 0) THEN
          ' Forward sweep: store in Data_1 (counts) and Data_3 (voltages)
          Data_1[step_index] = Par_8
          Data_3[step_index] = current_voltage
        ELSE
          ' Reverse sweep: store in Data_2 (counts) and Data_4 (voltages)
          Data_2[step_index] = Par_8
          Data_4[step_index] = current_voltage
        ENDIF
        
        ' Move to next step
        step_index = step_index + 1
        Par_15 = step_index
        
        ' Check if we've completed all steps for current direction
        IF (step_index >= Par_16) THEN
          ' Current direction complete
          IF (sweep_direction = 0) THEN
            ' Forward sweep complete, start reverse sweep
            sweep_direction = 1
            sweep_cycle = 1
            step_index = 0
            Par_15 = 0
            Par_17 = 1  ' Reverse sweep
            
            ' Start reverse sweep from +1V (SG384 safe)
            current_voltage = 1.0
            voltage_step = -2.0 / Par_16  ' Negative step for reverse sweep
            
          ELSE
            ' Reverse sweep complete, both sweeps done
            sweep_cycle = 2
            Par_19 = 1  ' Sweep complete
            
            ' Reset for next cycle
            step_index = 0
            Par_15 = 0
            sweep_direction = 0
            sweep_cycle = 0
            data_ready = 0
            current_voltage = -1.0
            voltage_step = 2.0 / Par_16
          ENDIF
          
        ELSE
          ' Move to next voltage step in current direction
          current_voltage = current_voltage + voltage_step
          
          ' CRITICAL: Clamp voltage to ±1V for SG384 safety
          IF (current_voltage > 1.0) THEN
            current_voltage = 1.0
          ENDIF
          IF (current_voltage < -1.0) THEN
            current_voltage = -1.0
          ENDIF
        ENDIF
        
        ' Update voltage parameter
        Par_18 = current_voltage
      ENDIF
      
      ' Reset for next averaging cycle
      Par_6 = 0
      Par_7 = 0
      sample_index = 1
    ELSE
      ' Continue accumulating for averaging
      Inc(sample_index)
    ENDIF
    
    ' Reset integration cycle counter
    integration_cycles = 0
  ENDIF
  
  ' Update current sample index
  Par_5 = sample_index
  
Finish:
  ' Cleanup
  Cnt_Enable(0)  ' Disable counter
  ' Set DAC1 output to 0V (center of range, SG384 safe)
  Write_DAC(1, 32768) 