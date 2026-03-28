import os
import sys
import struct
import matplotlib.pyplot as plt
srcpath = os.path.realpath(r'C:\Users\Duttlab\Downloads\PythonExamples\Examples\SourceFiles')
sys.path.append(srcpath)
from teproteus import TEProteusAdmin as TepAdmin
from tevisainst import TEVisaInst
import numpy as np
# testing aom with worst case scenario: longest pulse durations and shortest waiting time:
# from scc papers, longest shelving is 300 ns, longest ionization is 500 ns, short readout: 3ms, and short initialization 1 us
# Connect to instrument(PXI)
sid = 6 #PXI slot of AWT on chassis
admin = TepAdmin() #required to control PXI module
inst = admin.open_instrument(slot_id=sid)
resp = inst.send_scpi_query("*IDN?") # Get the instrument's *IDN
print('connected to: ' + resp) # Print *IDN

# initialize DAC
inst.send_scpi_cmd('*CLS; *RST')

#AWG channel
ch = 3 # everything after relates to CH 3
cmd = ':INST:CHAN {0}'.format(ch)
inst.send_scpi_cmd(cmd)
cmd = ':VOLT 1.0'
rc = inst.send_scpi_cmd(cmd)
#cmd = ':VOLT {0}'.format(1)
#inst.send_scpi_cmd(cmd)

sampleRateDAC = 1.25E9
cmd = ':FREQ:RAST {0}'.format(sampleRateDAC)
inst.send_scpi_cmd(cmd)
cmd = ':TRAC:DEL:ALL' # Clear CH 3 Memory
inst.send_scpi_cmd(cmd)
cmd = ':INIT:CONT OFF' # play waveform continuously
inst.send_scpi_cmd(cmd)

#scale to 16 bits
max_dac=65535 # Max Dac
half_dac=max_dac/2 # DC Level
data_type = np.uint16 # DAC data type

segnum = 1
amp = 0.6
# must be a multiple of 64 (corresponds to 300 ns)
segLen = 384
dacWaveDC = amp * np.ones(segLen)
dacWaveDC = np.clip(dacWaveDC, -1.0, 1.0)
dacWaveDC = ((dacWaveDC + 1.0) * half_dac).astype(data_type)
cmd = ':TRAC:DEF {0}, {1}'.format(segnum, len(dacWaveDC)) # memory location and length
inst.send_scpi_cmd(cmd)
cmd = ':TRAC:SEL {0}'.format(segnum)
inst.send_scpi_cmd(cmd)

inst.timeout = 30000 #increase
inst.write_binary_data('*OPC?; :TRAC:DATA', dacWaveDC) # write, and wait while *OPC completes
inst.timeout = 10000 # return to normal

# Create and download a second Segment
segnum = 2
amp = 1
# must be a multiple of 64 (corresponds to 500 ns)
segLen = 640
dacWaveDC = amp * np.ones(segLen)
dacWaveDC = np.clip(dacWaveDC, -1.0, 1.0)
dacWaveDC = ((dacWaveDC + 1.0) * half_dac).astype(data_type)
cmd = ':TRAC:DEF {0}, {1}'.format(segnum, len(dacWaveDC)) # memory location and length
inst.send_scpi_cmd(cmd)
cmd = ':TRAC:SEL {0}'.format(segnum)
inst.send_scpi_cmd(cmd)

inst.timeout = 30000 #increase
inst.write_binary_data('*OPC?; :TRAC:DATA', dacWaveDC) # write, and wait while *OPC completes
inst.timeout = 10000 # return to normal

# Create and download a third Segment
segnum = 3
amp = 0.3
segLen = 3750016  # must be a multiple of 64 (corresponds to 3 ms)
#dacWaveDC = amp * np.ones(segLen)
dacWaveDC = np.full(segLen, amp, dtype=float)
dacWaveDC = np.clip(dacWaveDC, -1.0, 1.0)
dacWaveDC = ((dacWaveDC + 1.0) * half_dac).astype(data_type)
cmd = ':TRAC:DEF {0}, {1}'.format(segnum, len(dacWaveDC)) # memory location and length
inst.send_scpi_cmd(cmd)
cmd = ':TRAC:SEL {0}'.format(segnum)
inst.send_scpi_cmd(cmd)

inst.timeout = 30000 #increase
inst.write_binary_data('*OPC?; :TRAC:DATA', dacWaveDC) # write, and wait while *OPC completes
inst.timeout = 10000 # return to normal

# Create and download a third Segment
segnum = 4
amp = 0
segLen = 1280  # must be a multiple of 64 (corresponds to 1 us)
dacWaveDC = amp * np.zeros(segLen)
print(f"voltage: {inst.send_scpi_query(":VOLT?")}")
dacWaveDC = np.clip(dacWaveDC, -1.0, 1.0)
dacWaveDC = ((dacWaveDC) * half_dac).astype(data_type) # +1.0
cmd = ':TRAC:DEF {0}, {1}'.format(segnum, len(dacWaveDC)) # memory location and length
inst.send_scpi_cmd(cmd)
cmd = ':TRAC:SEL {0}'.format(segnum)
inst.send_scpi_cmd(cmd)
inst.timeout = 30000 #increase
inst.write_binary_data('*OPC?; :TRAC:DATA', dacWaveDC) # write, and wait while *OPC completes
inst.timeout = 10000 # return to normal
cmd = ':VOLT:OFFS 0'
rc = inst.send_scpi_cmd(cmd)
print(f"offset: {inst.send_scpi_query(":VOLT:OFFS?")}")
#Create a Task Table
cmd = ':TASK:COMP:LENG 4' # set task table length
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:SEL 1' # set task 1
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:TYPE:STAR'
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:SEGM 1'
inst.send_scpi_cmd(cmd) # shelving pulse
cmd = ':TASK:COMP:NEXT1 2'
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:SEL 2' # set task 2
inst.send_scpi_cmd(cmd)
cmd = f':TASK:COMP:TYPE:SEQ'
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:SEGM 2'
inst.send_scpi_cmd(cmd) # ionization pulse
cmd = ':TASK:COMP:NEXT1 3'
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:SEL 3' # set task 3
inst.send_scpi_cmd(cmd)
cmd = f':TASK:COMP:TYPE:SEQ'
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:SEGM 3'
inst.send_scpi_cmd(cmd) # readout pulse
cmd = ':TASK:COMP:NEXT1 4'
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:SEL 4' # set task 4
inst.send_scpi_cmd(cmd)
cmd = f':TASK:COMP:TYPE:END'
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:SEGM 4'
inst.send_scpi_cmd(cmd) # DC: wait for the green and microwave
cmd = ':TASK:COMP:NEXT1 1'
inst.send_scpi_cmd(cmd)
cmd = f':TASK:COMP:SEQ {1}'
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:WRITE' #write to FPGA
inst.send_scpi_cmd(cmd)
cmd = ':SOUR:FUNC:MODE TASK'
inst.send_scpi_cmd(cmd)
cmd = ':OUTP ON'
rc = inst.send_scpi_cmd(cmd)

inst.close_instrument()
admin.close_inst_admin()
