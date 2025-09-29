' <ADbasic Header, Headerversion 001.001>
' Process_Number         = 1
' Initial_Processdelay   = 300000
' Eventsource            = Timer
' Priority               = Normal
' ADbasic_Version        = 6.3.0
' <Header End>

#Include ADwinGoldII.inc

Rem ------------------------------
Rem Parameters (PC -> ADwin)
Rem   FPar_1 : Vout (desired volts, will be clamped to ±1.0)
Rem   Par_2  : SETTLE_US
Rem   Par_3  : DWELL_US
Rem   Par_4  : DAC channel (1..2)
Rem   Par_5  : Edge select for CLK (0=rising, 1=falling)
Rem   Par_8  : Tick (µs) -> Processdelay = Par_8 * 100 (default 200)
Rem   Par_10 : START (1 = run one window, 0 = idle)
Rem Results (ADwin -> PC)
Rem   Par_20 : READY flag (1 when the window result is ready; clear to 0 for next)
Rem   Par_21 : DWELL_US echoed
Rem   Par_22 : SETTLE_US echoed
Rem   Par_25 : Heartbeat
Rem   Par_26 : Current state (debug)
Rem   Par_30 : Last window count (dwell-only)
Rem ------------------------------

Function VoltsToDigits(v) As Long
  VoltsToDigits = Round((v + 10.0) * 65535.0 / 20.0)
EndFunction

Rem clamp to [lo, hi]
Function Clamp(v, lo, hi) As Float
  IF (v < lo) THEN
    v = lo
  ENDIF
  IF (v > hi) THEN
    v = hi
  ENDIF
  Clamp = v
EndFunction

Dim state As Long
Dim tick_us As Long
Dim settle_us, dwell_us As Long
Dim settle_rem_us, dwell_rem_us As Long
Dim dac_ch As Long
Dim v_req As Float
Dim v_clamped As Float
Dim dac_code As Long
Dim old_cnt, new_cnt, diff As Long

Init:
  Rem default tick = 200 µs if unset
  IF (Par_8 <= 0) THEN
    Par_8 = 200
  ENDIF
  Processdelay = Par_8 * 100
  Rem 10 ns units

  Par_20 = 0
  Par_25 = 0
  Par_30 = 0
  state  = 0

  Rem Counter setup: clock/direction, single-ended
  Cnt_Enable(0)
  Cnt_Clear(0001b)
  IF (Par_5 = 1) THEN
    Cnt_Mode(1, 00000100b)
    Rem invert A/CLK -> count on falling edges
  ELSE
    Cnt_Mode(1, 00000000b)
    Rem rising edges
  ENDIF
  Cnt_SE_Diff(0000b)
  Cnt_Enable(0001b)

Event:
  Par_25 = Par_25 + 1

  tick_us = Processdelay / 100
  IF (tick_us <= 0) THEN
    tick_us = 1
  ENDIF

  Par_26 = state
  Rem live state (debug)

  IF (Par_10 = 0) THEN
    state = 0
  ELSE
    SelectCase state

      Case 0
        Rem ARM MEASUREMENT
        settle_us = Par_2
        dwell_us  = Par_3

        IF (Par_4 < 1) THEN
          dac_ch = 1
        ELSE
          IF (Par_4 > 2) THEN
            dac_ch = 2
          ELSE
            dac_ch = Par_4
          ENDIF
        ENDIF

        v_req = FPar_1
        v_clamped = Clamp(v_req, -1.0, 1.0)
        dac_code = VoltsToDigits(v_clamped)
        Write_DAC(dac_ch, dac_code)
        Start_DAC()

        settle_rem_us = settle_us
        dwell_rem_us  = dwell_us

        Par_21 = dwell_us
        Par_22 = settle_us
        Par_20 = 0

        state = 10

      Case 10
        Rem SETTLE countdown (excluded from counting)
        IF (settle_rem_us > 0) THEN
          IF (settle_rem_us > tick_us) THEN
            settle_rem_us = settle_rem_us - tick_us
          ELSE
            settle_rem_us = 0
          ENDIF
        ELSE
          state = 20
        ENDIF

      Case 20
        Rem LATCH BASELINE (start of dwell)
        Cnt_Latch(0001b)
        old_cnt = Cnt_Read_Latch(1)
        state = 30

      Case 30
        Rem DWELL countdown (counting window)
        IF (dwell_rem_us > 0) THEN
          IF (dwell_rem_us > tick_us) THEN
            dwell_rem_us = dwell_rem_us - tick_us
          ELSE
            dwell_rem_us = 0
          ENDIF
        ELSE
          state = 40
        ENDIF

      Case 40
        Rem LATCH END + STORE RESULT
        Cnt_Latch(0001b)
        new_cnt = Cnt_Read_Latch(1)
        diff = new_cnt - old_cnt
        IF (diff < 0) THEN
          diff = -diff
        ENDIF
        Par_30 = diff
        Par_20 = 1
        Rem READY
        state  = 90

      Case 90
        Rem WAIT FOR PC TO CLEAR READY OR STOP
        IF (Par_10 = 0) THEN
          state = 0
        ELSE
          IF (Par_20 = 0) THEN
            state = 0
          ENDIF
        ENDIF

      CaseElse
        state = 0

    EndSelect
  ENDIF

End

Finish:
  Par_10 = 0
  Par_20 = 0
  Cnt_Enable(0)
  Cnt_Clear(0001b)

  IF (Par_4 < 1) THEN
    dac_ch = 1
  ELSE
    IF (Par_4 > 2) THEN
      dac_ch = 2
    ELSE
      dac_ch = Par_4
    ENDIF
  ENDIF
  Write_DAC(dac_ch, VoltsToDigits(0.0))
  Start_DAC()
  state = 0

  Exit