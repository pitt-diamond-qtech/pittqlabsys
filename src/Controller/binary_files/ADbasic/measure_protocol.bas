' Measure Protocol for ODMR Pulsed Experiment
' This ADbasic program handles photon counting during AWG520 trigger pulses
' and stores counts for each scan point in the experiment.
'
' Hardware Setup:
' - AWG520 triggers ADwin via digital output
' - ADwin counts photons during trigger pulse
' - Counts stored for each scan point
' - Supports 50,000 repetitions per scan point for statistics
'
' Parameters (set via ADbasic):
' - count_time: Duration of counting window in microseconds
' - reset_time: Time between counts in microseconds  
' - repetitions_per_point: Number of repetitions per scan point (default: 50000)
' - microwave_frequency: Microwave frequency in Hz
' - microwave_power: Microwave power in dBm
' - laser_power: Laser power in mW
' - laser_wavelength: Laser wavelength in nm

' ADbasic Header
#HEADER_START
#HEADER_VERSION 001.001
#HEADER_END

' Variable declarations
DIM count_time AS LONG        ' Counting time in microseconds
DIM reset_time AS LONG        ' Reset time between counts in microseconds
DIM repetitions_per_point AS LONG  ' Repetitions per scan point
DIM current_scan_point AS LONG     ' Current scan point index
DIM total_scan_points AS LONG      ' Total number of scan points
DIM photon_counts[1000] AS LONG    ' Array to store counts (max 1000 scan points)
DIM current_repetition AS LONG     ' Current repetition within scan point
DIM trigger_detected AS BOOL       ' Flag for AWG520 trigger detection
DIM count_start_time AS LONG       ' Start time for counting
DIM count_end_time AS LONG         ' End time for counting

' Initialize parameters
count_time = 300        ' 300 microseconds counting time
reset_time = 2000       ' 2 milliseconds reset time
repetitions_per_point = 50000  ' 50K repetitions for statistics
current_scan_point = 0
total_scan_points = 0
current_repetition = 0
trigger_detected = FALSE

' Main program loop
DO
    ' Wait for AWG520 trigger on digital input
    IF DIGIN(1) = 1 AND NOT trigger_detected THEN
        trigger_detected = TRUE
        current_repetition = 0
        
        ' Start counting for this scan point
        count_start_time = TIMER
        count_end_time = count_start_time + count_time
        
        ' Count photons during trigger pulse
        WHILE TIMER < count_end_time
            ' Increment counter for each photon detected
            ' This assumes photon detector is connected to counter input
            IF COUNTER(1) > 0 THEN
                photon_counts[current_scan_point] = photon_counts[current_scan_point] + COUNTER(1)
                COUNTER(1) = 0  ' Reset counter
            ENDIF
        WEND
        
        ' Wait for reset time
        WAIT(reset_time)
        
        ' Check if we've completed all repetitions for this scan point
        current_repetition = current_repetition + 1
        IF current_repetition >= repetitions_per_point THEN
            ' Move to next scan point
            current_scan_point = current_repetition + 1
            current_repetition = 0
            
            ' Check if experiment is complete
            IF current_scan_point >= total_scan_points THEN
                ' Experiment complete - save data
                SAVE_DATA
                BREAK
            ENDIF
        ENDIF
        
        trigger_detected = FALSE
    ENDIF
    
    ' Small delay to prevent busy waiting
    WAIT(100)
LOOP

' Subroutine to save experimental data
SUB SAVE_DATA()
    DIM i AS LONG
    DIM filename AS STRING
    
    ' Create filename with timestamp
    filename = "odmr_pulsed_data_" + STR$(TIMESTAMP()) + ".txt"
    
    ' Open file for writing
    OPEN filename FOR OUTPUT AS #1
    
    ' Write header
    PRINT #1, "ODMR Pulsed Experiment Data"
    PRINT #1, "Timestamp: " + STR$(TIMESTAMP())
    PRINT #1, "Count time: " + STR$(count_time) + " microseconds"
    PRINT #1, "Reset time: " + STR$(reset_time) + " microseconds"
    PRINT #1, "Repetitions per point: " + STR$(repetitions_per_point)
    PRINT #1, ""
    PRINT #1, "Scan Point,Photon Count,Average Count"
    
    ' Write data
    FOR i = 0 TO current_scan_point - 1
        PRINT #1, STR$(i) + "," + STR$(photon_counts[i]) + "," + STR$(photon_counts[i] / repetitions_per_point)
    NEXT i
    
    ' Close file
    CLOSE #1
END SUB
