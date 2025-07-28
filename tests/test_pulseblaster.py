from src.Controller.pulse_blaster import *
import pytest
import time
import sys
import struct

"""This script will initiailize the PB board and begin running whatever instructions have been loaded into the
parameters. Parameters are PB clock speed (MHz) and run time (s)"""

@pytest.mark.parametrize("clock", "run_time", [(10.0, 5.0)])
def test_pulse_sequence(clock, run_time):
    if struct.calcsize("P") * 8 == 64:
        libraryFileName = 'spinapi64.dll'
    else:
        libraryFileName = 'spinapi.dll'

    pb = PulseBlaster(library_file = libraryFileName)

    try:
        pb.close()
    except RuntimeError:
        print('Board already closed')

    if pb.init() == None:
        print('Board initialized')
    if pb.set_clock(clock) == None:
        print('PB clock set to: %f MHz' % clock)
    pb.stop()

    if pb.start() == None:
        print('Pulse sequence started, running for %f seconds' % run_time)
    time.sleep(run_time)
    pb.stop()
    if pb.close() == None:
        print('Board closed')
    print('Pulse sequence finished')