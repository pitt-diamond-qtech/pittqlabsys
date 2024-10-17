from src.Controller.pulse_blaster import *
import time
import sys
import struct

"""This script will initalize the PulseBlaster board and begin running the instructions loaded onto the command line.
Command line arguments are clock (MHz) and runtime (s)"""

input_params = sys.argv
try:
    clock = float(input_params[1])
    run_time = float(input_params[2])
except IndexError:
    print('input_params')
    print('NOT ENOUGH INPUT PARAMETERS! SEQUENCE NOT STARTED.')
except ValueError:
    print('input_params')
    print('ERROR PARSING INPUT PARAMETERS! INPUTS SHOULD BE NUMBER VALUES.')
else:
    print('clock: ', clock)
    print('run_time: ', run_time)

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
        print('PB clock set to: %f MHz'% clock)
    pb.stop()
    if pb.start() == None:
        print('Pulse sequence started, running for %f seconds' % run_time)
    time.sleep(run_time)
    pb.stop()
    if pb.close() == None:
        print('Board closed')
    print('Pulse sequence finished')

