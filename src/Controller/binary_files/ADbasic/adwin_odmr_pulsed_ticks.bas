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
' adwin_triggering_proteus.bas
' This process generates trigger pulses to control proteus external triggering
' for testing the ADwin -> proteus control architecture.
'
' Hardware Setup:
' - ADwin Digital Output -> Proteus TRIG 1 IN (front panel)
' - Proteus configured for external trigger with Wait Trigger enabled
' for this file, we use ticks for wait
' Operation:
' - Process generates trigger pulses at specified intervals
' - Each trigger causes Proteus to advance to next sequence line
' - Computer can control timing and number of triggers via parameters
' This is the new approach: adwin triggers awg to move to next task/line
#Include ADwinGoldII.inc
' Variables exchanged with python
' Par_3: count_time (with calibration offset)
' Par_4: reset_time (with calibration offset): time between signal counts and reference counts
' Par_5: repeat_count
' Par_6: number of iterations
' Par_7: acquisition done flag
' Par_8: repetition_counter
' Data_1: signal counts
' Data_2: reference counts
' Par_9: sequence_duration (with calibration offset): Time of the awg sequence
' Par_10: proteus response delay
' Par_11: START: 1, IDLE: 0
' Par_26 = state
DIM number_of_signal_events AS LONG
DIM iteration_number, i as LONG
DIM count_time, reset_time, sequence_duration, proteus_delay, sleep_duration AS FLOAT
DIM trigger_duration, delay AS FLOAT
DIM Data_1[20] AS LONG ' 100000 is the maximum number of iterations
DIM Data_2[20] AS LONG ' 100000 is the maximum number of iterations


'--- working vars ---
Dim settle_us, dwell_us, signal_or_reference_counts As Long
Dim old_cnt, new_cnt As Long
Dim fd As Float
Dim sum_counts, max_counts As Long

'--- state machine vars ---
Dim state, prev_state As Long
Dim settle_rem_us, dwell_rem_us, tick_us As Long
Dim overhead_factor As Float
Dim hb_div As Long ' heartbeat prescaler to avoid spamming
Dim pd_us, pd_ticks As Long


Init:
  signal_or_reference_counts = 0
  Cnt_Enable(0)
  Cnt_Clear(0001b)
  Cnt_Mode(1, 00001000b)   ' invert DIR: DIR low = count up
  Par_7 = 0       ' acquisition done flag
  Par_8 = 0       ' repetition_counter
  iteration_number = 0
  number_of_signal_events = Par_5 * Par_6
  count_time = Par_3 ' (Par_3-10)
  reset_time = Par_4 ' (Par_4-30)
  sequence_duration = Par_9
  proteus_delay = Par_10
  trigger_duration = 10 'ns
  delay = sequence_duration - proteus_delay - (2*count_time) - reset_time - trigger_duration
  ' Auto-calculate pd based on dwell time for optimal chunking aiming for ~10 chunks per dwell
  pd_us = (delay /1000) / 10   ' max wait / 10

  ' Convert 탎 to ticks (approximate: 1탎 = 300 ticks)
  pd_ticks = pd_us * 300
  trigger_duration = trigger_duration/1000 ' us

  ' Clamp to reasonable bounds
  IF (pd_ticks < 1) THEN pd_ticks = 1      ' min 3.3ns
  IF (pd_ticks > 5000000) THEN pd_ticks = 5000000 ' max 16.7ms

  ' Debug: store calculation steps
  Par_72 = pd_us      ' calculated 탎
  Par_73 = pd_ticks   ' calculated ticks

  ' Set Processdelay directly in Init
  Processdelay = pd_ticks
  Par_71 = Processdelay

  ' Calculate tick_us
  ' overhead correction factor
  overhead_factor = 1.2
  ' Calculate base tick_us, then apply overhead correction
  tick_us = Round(Processdelay * 3.3 / 1000.0 * overhead_factor)   ' Apply overhead correction
  IF (tick_us <= 0) THEN
    tick_us = 1                  ' never allow zero tick
  ENDIF


  dwell_us = Par_3/1000

  settle_us = delay/1000
  Conf_DIO(1100b) ' configure 0 - 15 as DIGIN, and 16 - 31 as DIGOUT
  ' Set digital output 21 to low (no trigger)
  DIGOUT(21, 0)
  DIGOUT(16, 0)

  ' Counter 1: clk/dir, single-ended mode (basic setup)
  Cnt_SE_Diff(0000b)

  ' Watchdog (debug): 5 s (units = 10 쨉s) - increased for longer dwell times
  Watchdog_Init(1, 500000, 1111b)

  ' Initialize state machine
  state = 255
  hb_div = 0

  old_cnt = 0
  i = 1
  DO
    Data_1[i] = 0
    Data_2[i] = 0
    i = i +1
  UNTIL (i = 21)

Event:
  ' ---- heartbeat ----
  hb_div = hb_div + 1
  IF (hb_div >= 10) THEN         ' update heartbeat every ~10 ticks
    Par_25 = Par_25 + 1
    hb_div = 0
  ENDIF

  Par_26 = state                 ' live: which CASE we are in
  Watchdog_Reset()  ' Reset watchdog in Event

  ' ---- async stop: force state = 255 if Par_11 = 0 ----
  IF (Par_11 = 0) THEN
    state = 255
  ENDIF

  ' ---- run state machine unconditionally ----
  Par_26 = state   ' Debug: current state
  SelectCase state

    Case 255     ' IDLE: async start detection and housekeeping
      Rem breathe and advertise that we are alive
      IO_Sleep(1000)   ' 10 탎 yield
      Watchdog_Reset()   ' Reset watchdog in idle state
      Par_26 = state
      ' Check for async start: Par_11 flipped to 1
      IF (Par_11 = 1) THEN
        state = 10   ' Start new sweep
      ENDIF

    Case 10
      Par_8 = Par_8 + 1          ' current event number (increase for signal count)
      iteration_number = iteration_number + 1 ' Since Data_1 and Data_2 start at index 1
      ' reset counter
      Par_26 = state
      Cnt_Enable(0)
      Cnt_Clear(0001b)
      DIGOUT(21, 1)
      dwell_rem_us = trigger_duration
      prev_state = 10
      state = 20

    Case 20
      DIGOUT(21, 0)
      Watchdog_Reset()   ' Reset watchdog during long dwell
      Par_26 = state
      IF (dwell_rem_us >= tick_us) THEN
        dwell_rem_us = dwell_rem_us - tick_us
        state = 20
      ELSE
        prev_state = 20
        IF (prev_state = 10) THEN
          state = 30
        ELSE
          state = 34
        ENDIF
      ENDIF

    Case 30     ' START SETTLE
      Par_26 = state
      IF (prev_state = 20) THEN
        settle_rem_us = delay/1000
      ELSE
        settle_rem_us = reset_time/1000
      ENDIF
      prev_state = 30
      state = 31

    Case 31     ' SETTLE (time-sliced)
      Watchdog_Reset()   ' Reset watchdog during long settle
      Par_26 = state
      IF (settle_rem_us > tick_us) THEN
        settle_rem_us = settle_rem_us - tick_us
        state = 31
      ELSE
        prev_state = 31
        state = 32
      ENDIF

    Case 32     ' OPEN DWELL WINDOW (start fresh)
      ' Start a fresh window: clear -> enable -> dwell
      Cnt_Enable(0)
      Cnt_Clear(0001b)
      Cnt_Enable(0001b)
      DIGOUT(16, 1)

      ' latch once to prove it's zero:
      ' Cnt_Latch(0001b) : old_cnt = Cnt_Read_Latch(1)  ' should be 0
      ' we simply treat baseline as 0:
      old_cnt = 0
      Par_26 = state
      dwell_rem_us = count_time/1000
      prev_state = 32
      state = 20

    Case 34     ' CLOSE WINDOW, READ, STORE
      Cnt_Latch(0001b)
      new_cnt = Cnt_Read_Latch(1)
      Cnt_Enable(0)        ' Disable counter after dwell window
      DIGOUT(16,0)
      Par_26 = state
      Rem ---- compute delta with wrap handling using Float arithmetic ----
      fd = new_cnt - old_cnt


      IF (signal_or_reference_counts = 0) THEN 
        Data_1[iteration_number] = Data_1[iteration_number] + Round(fd)
        signal_or_reference_counts = 1
        DIGOUT(16, 1)
        prev_state = 34
        state = 30
      ELSE
        Data_2[iteration_number] = Data_2[iteration_number] + Round(fd)
        signal_or_reference_counts = 0
        IF (iteration_number = Par_6) THEN 'if we did all of our iterations for a given sequence, then go back to iteration 0
          iteration_number = 0
        ENDIF
      ENDIF
      IF (Par_8 = number_of_signal_events) THEN ' IF WE DID ALL OF OUR POINTS, FINISH
        IO_Sleep(1000)            ' ~10 탎 bus yield
        Watchdog_Reset()
        Par_7=1
        Cnt_Clear(0001b)
        DIGOUT(21, 0)                  ' Ensure trigger is low
        END
      ELSE ' ELSE, go back to case 10 where we trigger proteus again and restart sequence
        prev_state = 34
        state = 10
      ENDIF

    CaseElse
      Par_26 = 0
      state = 255

  EndSelect



Finish:
  ' Mark stopped and clear handshake
  Par_11 = 0
  Par_7 = 1
  Cnt_Enable(0)
  Cnt_Clear(0001b)
  DIGOUT(21, 0)
  ' De-arm watchdog so nothing can fire after process stops
  ' if 0 is not allowed as timeout on system, use 1 instead
  Watchdog_Init(1,0,0000b)

  Exit
