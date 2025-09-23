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
' ODMR Sweep Counter Script for Enhanced ODMR Experiments (State Machine)
' Generates a triangle on DACx (default DAC1) and counts falling edges on Counter 1.
' Non-blocking handshake: PC clears Par_20 to release next sweep.
' State machine prevents Get_Par timeouts by doing small chunks per Event.
'
#Include ADwinGoldII.inc

' ===================== Exposed interface =====================
' From Python:
'   FPar_1 = Vmin [V]   (clamped to [-1, +1])
'   FPar_2 = Vmax [V]   (clamped to [-1, +1])
'   Par_1  = N_STEPS    (>=2)
'   Par_2  = SETTLE_US  (us)
'   Par_3  = DWELL_US   (us)
'   Par_4  = DAC_CH     (1..2)
'   Par_8  = CHUNK_US   (µs, default 500 if 0)
'   Par_10 = START      (1=run, 0=idle)
' To Python:
'   Data_1[] = counts per step (LONG)
'   Data_2[] = DAC digits per step (LONG)
'   Par_20   = 1 when sweep done (PC must clear to 0 to allow next sweep)
'   Par_21   = number of points in last sweep (2*N_STEPS-2)
'   Par_25   = heartbeat counter (increments every Event tick)
' ============================================================

' ---- helpers (typed return OK; no typed args) ----
Function VoltsToDigits(v) As Long
  VoltsToDigits = Round((v + 10.0) * 65535.0 / 20.0)
EndFunction

Function DigitsToVolts(d) As Float
  DigitsToVolts = (d * 20.0 / 65535.0) - 10.0
EndFunction

' clamp to [lo, hi]
Function Clamp(v, lo, hi) As Float
  IF (v < lo) THEN
    v = lo
  ENDIF
  IF (v > hi) THEN
    v = hi
  ENDIF
  Clamp = v
EndFunction

' ---- working vars ----
Dim n_steps, n_points, k      As Long
Dim dac_ch                    As Long
Dim settle_us, dwell_us       As Long
Dim old_cnt, new_cnt, diff   As Long
Dim vmin_dig, vmax_dig        As Long
Dim step_dig, pos             As Long
Dim vmin_clamped, vmax_clamped, t As Float

' ---- state machine vars ----
Dim state As Long
Dim settle_rem_us, dwell_rem_us, chunk_us, chunk As Long

' ---- result buffers (1-based indexing) ----
Dim Data_1[100000] As Long     ' counts per step
Dim Data_2[100000] As Long     ' DAC digits per step

Init:
  ' Event timing isn't critical; waits use IO_Sleep (10 ns units)
  Processdelay = 10000

  ' Counter 1: clk/dir, count up on rising edges (DIR tied high)
  Cnt_Enable(0)
  Cnt_Clear(0001b)
  Cnt_Mode(1, 00000000b)   ' bit0=0 clk/dir, no inversions (count up)
  Cnt_SE_Diff(0000b)       ' single-ended
  Cnt_Enable(0001b)

  ' Watchdog (debug-friendly: 5 s). Keep Reset calls in code.
  Watchdog_Init(1, 500000, 1111b)   ' time units = 10 µs

  ' Initialize state machine
  state = 0

  ' Handshake init
  Par_20 = 0
  Par_21 = 0
  Par_25 = 0
  old_cnt = 0

Event:
  ' Heartbeat so the PC can see Event is running
  Par_25 = Par_25 + 1

  ' Chunk size (µs) from PC; default 500 µs if not set
  chunk_us = Par_8
  IF (chunk_us <= 0) THEN
    chunk_us = 500
  ENDIF

  ' If STOP, just idle this tick
  IF (Par_10 = 0) THEN
    state = 0
    IO_Sleep(1000)          ' ~10 µs
    Watchdog_Reset()
  ELSE

    SELECTCASE state

      ' ------------------------------------------------------
      CASE 0   ' START NEW SWEEP (when Par_20 == 0)
        IF (Par_20 <> 0) THEN
          state = 90
        ELSE
          ' --- snapshot & clamp ---
          n_steps   = Par_1
          IF (n_steps < 2) THEN
            n_steps = 2
          ENDIF
          settle_us = Par_2
          dwell_us  = Par_3
          dac_ch    = Par_4
          IF (dac_ch < 1) THEN
            dac_ch = 1
          ENDIF
          IF (dac_ch > 2) THEN
            dac_ch = 2
          ENDIF

          vmin_clamped = Clamp(FPar_1, -1.0, 1.0)
          vmax_clamped = Clamp(FPar_2, -1.0, 1.0)
          IF (vmin_clamped > vmax_clamped) THEN
            t = vmin_clamped
            vmin_clamped = vmax_clamped
            vmax_clamped = t
          ENDIF

          vmin_dig = VoltsToDigits(vmin_clamped)
          vmax_dig = VoltsToDigits(vmax_clamped)
          IF (vmin_dig = vmax_dig) THEN
            n_steps = 2
          ENDIF

          n_points = (2 * n_steps) - 2
          IF (n_points < 2) THEN
            n_points = 2
          ENDIF
          Par_21 = n_points

          ' Start with first step
          k = 0
          state = 20
        ENDIF

      ' ------------------------------------------------------
      CASE 20   ' PREP CURRENT STEP: compute pos, code; output; start settle
        IF (k < n_steps) THEN
          pos = k
        ELSE
          pos = (2 * n_steps) - 2 - k
        ENDIF

        IF (n_steps > 1) THEN
          step_dig = ((vmax_dig - vmin_dig) * pos) / (n_steps - 1)
        ELSE
          step_dig = 0
        ENDIF
        Data_2[k+1] = vmin_dig + step_dig
        
        ' bounds check for DAC digits (should be 0-65535)
        IF (Data_2[k+1] < 0) THEN
          Data_2[k+1] = 0
        ENDIF
        IF (Data_2[k+1] > 65535) THEN
          Data_2[k+1] = 65535
        ENDIF

        Write_DAC(dac_ch, Data_2[k+1])
        Start_DAC()

        settle_rem_us = settle_us
        state = 30

      ' ------------------------------------------------------
      CASE 30   ' SETTLE (excluded from counting)
        IF (settle_rem_us > 0) THEN
          chunk = settle_rem_us
          IF (chunk > chunk_us) THEN
            chunk = chunk_us
          ENDIF
          IO_Sleep(chunk * 100)          ' 1 µs = 100 * 10 ns
          settle_rem_us = settle_rem_us - chunk
          Watchdog_Reset()
        ELSE
          state = 40
        ENDIF

      ' ------------------------------------------------------
      CASE 40   ' LATCH BASELINE (start-of-dwell)
        Cnt_Latch(0001b)
        old_cnt = Cnt_Read_Latch(1)
        dwell_rem_us = dwell_us
        state = 50

      ' ------------------------------------------------------
      CASE 50   ' DWELL (counting window) in chunks
        IF (dwell_rem_us > 0) THEN
          chunk = dwell_rem_us
          IF (chunk > chunk_us) THEN
            chunk = chunk_us
          ENDIF
          IO_Sleep(chunk * 100)
          dwell_rem_us = dwell_rem_us - chunk
          Watchdog_Reset()
        ELSE
          state = 60
        ENDIF

      ' ------------------------------------------------------
      CASE 60   ' LATCH END (end-of-dwell), store delta
        Cnt_Latch(0001b)
        new_cnt = Cnt_Read_Latch(1)
        diff = new_cnt - old_cnt         ' LONG math: wrap handled
        IF (diff < 0) THEN
          diff = -diff
        ENDIF
        Data_1[k+1] = diff
        state = 70

      ' ------------------------------------------------------
      CASE 70   ' ADVANCE STEP
        k = k + 1
        IF (k >= n_points) THEN
          ' Finish sweep
          Par_20 = 1              ' READY
          state  = 90             ' wait for PC
        ELSE
          state = 20              ' next step
        ENDIF

      ' ------------------------------------------------------
      CASE 90   ' WAIT FOR PC TO CLEAR Par_20
        IF (Par_20 = 0) THEN
          state = 0               ' start next sweep
        ELSE
          IO_Sleep(1000)          ' ~10 µs
          Watchdog_Reset()
        ENDIF

      ' ------------------------------------------------------
      CASE ELSE
        state = 0

    ENDSELECT

  ENDIF
  ' (no End here; Event returns to scheduler automatically)