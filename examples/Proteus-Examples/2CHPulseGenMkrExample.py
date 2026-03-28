import os
import sys
import struct
srcpath = os.path.realpath(r'C:\Users\Duttlab\Downloads\PythonExamples\Examples\SourceFiles')
sys.path.append(srcpath)
from teproteus import TEProteusAdmin as TepAdmin
from tevisainst import TEVisaInst

import numpy as np

#Set rates for DAC 
sampleRateDAC = 1E9
#wavefore parameters
max_dac=(2**16)-1 # Max Dac
half_dac=max_dac/2 # DC Level
min_dac = 0
data_type = np.uint16 # DAC data type

# Make CH1 pulse
onLen = 30016
offLen = 30016

dacWaveOn = np.ones(onLen)
dacWaveOn = dacWaveOn * max_dac 
dacWaveOn = dacWaveOn.astype(data_type)

dacWaveOff = np.zeros(offLen)
dacWaveOff = dacWaveOff * min_dac 
dacWaveOff = dacWaveOff.astype(data_type)   

dacWave1 = np.concatenate([dacWaveOn, dacWaveOff])   
 

# Connect to instrument(PXI)
sid = 6 #PXI slot of AWT on chassis <------------ SLOT NUMBER HERE
admin = TepAdmin() #required to control PXI module
inst = admin.open_instrument(slot_id=sid) 
resp = inst.send_scpi_query("*IDN?") # Get the instrument's *IDN
print('connected to: ' + resp) # Print *IDN


"""# Connect to instrument(LAN)
inst_addr = 'TCPIP::192.168.1.12::5025::SOCKET' #Proteus Lan
#inst_addr = 'TCPIP::127.0.0.1::5025::SOCKET' #Proteus Local """

"""
inst = TEVisaInst(inst_addr) # get instruent pointer
resp = inst.send_scpi_query("*IDN?")
print('Connected to: ' + resp) # print insturmrnt ID"""

resp = inst.send_scpi_query("*OPT?")
print('Options: ' + resp) # print insturmrnt ID

# initialize DAC
inst.send_scpi_cmd('*CLS; *RST')

#AWG channel
ch = 1 # everythinf after relates to CH 1
cmd = ':INST:CHAN {0}'.format(ch)
inst.send_scpi_cmd(cmd)

cmd = ':FREQ:RAST {0}'.format(sampleRateDAC) 
inst.send_scpi_cmd(cmd)
inst.send_scpi_cmd(':INIT:CONT ON')
inst.send_scpi_cmd(':TRAC:DEL:ALL')


# Define segment memory
segnum = 1
cmd = ':TRAC:DEF {0}, {1}'.format(segnum, len(dacWave1))
inst.send_scpi_cmd(cmd)

# Select the segment
cmd = ':TRAC:SEL {0}'.format(segnum)
inst.send_scpi_cmd(cmd)

# Increase the timeout before writing binary-data:
inst.timeout = 30000
# Send the binary-data with *OPC? added to the beginning of its prefix.
inst.write_binary_data('*OPC?; :TRAC:DATA', dacWave1)
# Set normal timeout
inst.timeout = 10000

resp = inst.send_scpi_query(':SYST:ERR?')
print("Trace Download Error = ")
print(resp)

markerNum = 1
mark = np.zeros(len(dacWave1) // 4, np.int8)
mark[0:12800] = 17  # 00010001 <- Marker 1 set bit 0 and 4,

# Increase the timeout before writing binary-data:
inst.timeout = 30000
# Send the binary-data with *OPC? added to the beginning of its prefix.
inst.write_binary_data('*OPC?; :MARK:DATA', mark)
# Set normal timeout
inst.timeout = 10000

resp = inst.send_scpi_query(':SYST:ERR?')
print("Marker Download Error = ")
print(resp)

# Select the marker to assign to above trace
cmd = ':MARK:SEL {0}'.format(markerNum)
inst.send_scpi_cmd(cmd)

cmd = ':MARK:STAT ON'
inst.send_scpi_cmd(cmd)

resp = inst.send_scpi_query(':SYST:ERR?')
print("Marker Error = ")
print(resp)

cmd = ':FUNC:MODE:SEGM {0}'.format(segnum)
inst.send_scpi_cmd(cmd)

cmd = ':VOLT MAX'
rc = inst.send_scpi_cmd(cmd)

cmd = ':VOLT:OFFS 0.0'
rc = inst.send_scpi_cmd(cmd)

cmd = ":MARK:VOLT:PTOP 1.2"
rc = inst.send_scpi_cmd(cmd)

cmd = ":MARK:VOLT:OFFS 0.5"
rc = inst.send_scpi_cmd(cmd)
    
cmd = ':OUTP ON'
rc = inst.send_scpi_cmd(cmd)

resp = inst.send_scpi_query(':SYST:ERR?')
print("End of CH1, Gen Error = ")
print(resp)