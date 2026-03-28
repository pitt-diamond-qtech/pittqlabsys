import os
import sys
import struct
srcpath = os.path.realpath(r'C:\Users\Duttlab\Downloads\PythonExamples\Examples\SourceFiles')
sys.path.append(srcpath)
from teproteus import TEProteusAdmin as TepAdmin
from tevisainst import TEVisaInst
import numpy as np
# testing aom with worst case scenario: longest pulse durations and shortest waiting time:
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
cmd = ':VOLT MAX'
rc = inst.send_scpi_cmd(cmd)

sampleRateDAC = 1.25E9
cmd = ':FREQ:RAST {0}'.format(sampleRateDAC)
inst.send_scpi_cmd(cmd)
cmd = ':TRAC:DEL:ALL' # Clear CH 1 Memory
inst.send_scpi_cmd(cmd)
cmd = ':INIT:CONT OFF' # play waveform continuously
inst.send_scpi_cmd(cmd)

#scale to 16 bits
max_dac=65535 # Max Dac
half_dac=max_dac/2 # DC Level
data_type = np.uint16 # DAC data type

segnum = 1
amp = 1
segLen = 1024 # must be a multiple of 64
dacWaveDC = amp * np.ones(segLen)
dacWaveDC = dacWaveDC * half_dac  # scale
dacWaveDC = dacWaveDC.astype(data_type)
cmd = ':TRAC:DEF {0}, {1}'.format(segnum, len(dacWaveDC)) # memory location and length
inst.send_scpi_cmd(cmd)
cmd = ':TRAC:SEL {0}'.format(segnum)
inst.send_scpi_cmd(cmd)

inst.timeout = 30000 #increase
inst.write_binary_data('*OPC?; :TRAC:DATA', dacWaveDC) # write, and wait while *OPC completes
inst.timeout = 10000 # return to normal

# Create and download a second Segment
segnum = 2
amp = 0
segLen = 1024  # must be a multiple of 64
dacWaveDC = amp * np.zeros(segLen)
dacWaveDC = dacWaveDC * half_dac  # scale
dacWaveDC = dacWaveDC.astype(data_type)
cmd = ':TRAC:DEF {0}, {1}'.format(segnum, len(dacWaveDC)) # memory location and length
inst.send_scpi_cmd(cmd)
cmd = ':TRAC:SEL {0}'.format(segnum)
inst.send_scpi_cmd(cmd)

inst.timeout = 30000 #increase
inst.write_binary_data('*OPC?; :TRAC:DATA', dacWaveDC) # write, and wait while *OPC completes
inst.timeout = 10000 # return to normal

# Set the thrshhold level of the trigger
inst.send_scpi_cmd(':TRIG:LEV 0.1')

resp = inst.send_scpi_cmd(':INST:ACT {0}'.format(1))
# Select channel- Trigger source: EXT=TRG2 ,INT=CPU
cmd = ':INST:CHAN {0}'.format(ch)
inst.send_scpi_cmd(cmd)
inst.send_scpi_cmd('TRIG:SOUR:ENAB {}'.format('TRG2'))
inst.send_scpi_cmd('TRIG:SEL {}'.format('TRG2'))
inst.send_scpi_cmd('TRIG:STAT ON')
#Create a Task Table
cmd = ':TASK:COMP:LENG 2' # set task table length
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:SEL 1'
inst.send_scpi_cmd(cmd)
cmd = ':TASK:COMP:TYPE SING'
inst.send_scpi_cmd(cmd)
#@@@
cmd = ':TASK:COMP:ENAB TRG2'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
"""cmd = ':TASK:COMP:JUMP IMM'
inst.send_scpi_cmd(cmd)"""
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
cmd = ':TASK:COMP:DEST TRG'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
#@@
cmd = ':TASK:COMP:SEGM 1'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
cmd = ':TASK:COMP:NEXT2 2'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
cmd = ':TASK:COMP:SEL 2'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
cmd = ':TASK:COMP:TYPE SING'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
#@@@
cmd = ':TASK:COMP:ENAB TRG2'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
"""cmd = ':TASK:COMP:JUMP IMM'
inst.send_scpi_cmd(cmd)"""
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
cmd = ':TASK:COMP:DEST TRG'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
#@@
cmd = ':TASK:COMP:SEGM 2'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
cmd = ':TASK:COMP:NEXT2 1'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
cmd = ':TASK:COMP:WRITE'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
cmd = ':SOUR:FUNC:MODE TASK'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)

#$$$
"""inst.send_scpi_cmd(':TRIG:SOURce:ENAB {}'.format('TRG2'))
cmd = ':TRIGger[:ACTIVE]:SELect TRG2'
inst.send_scpi_cmd(cmd)

cmd = ':TRIGger[:ACTIVE]:STATe'
inst.send_scpi_cmd(cmd)

cmd = ':TRIGger:LEVel 0.5'
inst.send_scpi_cmd(cmd)
cmd = ':TRIGger:IMMediate'
inst.send_scpi_cmd(cmd)

cmd = ':TRIGger:IDLE CURR'
inst.send_scpi_cmd(cmd)"""
#$$$

cmd = ':OUTP ON'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)

"""# Set up the trigger
cmd = ':INST:CHAN {0}'.format(ch)
inst.send_scpi_cmd(cmd)
inst.send_scpi_cmd(':TRIG:COUP ON')
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
inst.send_scpi_cmd(':TRIG:SOURce:ENAB {}'.format('TRG2'))
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
inst.send_scpi_cmd(':TRIG:SEL {}'.format('TRG2'))
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
inst.send_scpi_cmd(':TRIG:LEV 0.5')
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
inst.send_scpi_cmd(':TRIG:STAT ON')
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)
cmd = '*TRG'
inst.send_scpi_cmd(cmd)
resp = inst.send_scpi_query(':SYST:ERR?')
print(resp)"""


inst.close_instrument()
admin.close_inst_admin()
