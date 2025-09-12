# Created by gurudevdutt at 7/30/25
import pytest
from unittest.mock import MagicMock
from src.Controller.mw_generator_base import MicrowaveGeneratorBase
from src.Controller.sg384 import SG384Generator
from src.Controller.windfreak_synth_usbii import WindfreakSynthUSBII

# --- Helpers to simulate transport ---
class DummySocket:
    def __init__(self, *args, **kwargs):
        self._recv_buffer = b""
        self.sent = []
    def connect(self, addr):
        pass
    def sendall(self, data):
        self.sent.append(data)
    def recv(self, num):
        # simulate query response ending with newline
        return b"DUMMY_IDN\n"
    def close(self):
        pass

@pytest.fixture
def mock_visa_instrument():
    """Create a mock VISA instrument for testing"""
    mock_inst = MagicMock()
    mock_inst.written = []
    mock_inst.write = MagicMock(side_effect=lambda cmd: mock_inst.written.append(cmd))
    mock_inst.query = MagicMock(return_value="DUMMY_IDN\n")
    mock_inst.close = MagicMock()
    return mock_inst

@pytest.fixture
def mock_resource_manager(mock_visa_instrument):
    """Create a mock resource manager"""
    mock_rm = MagicMock()
    mock_rm.open_resource = MagicMock(return_value=mock_visa_instrument)
    return mock_rm

@pytest.fixture(autouse=True)
def patch_transports(monkeypatch, mock_resource_manager):
    """Automatically patch all transport mechanisms for testing"""
    import socket
    monkeypatch.setattr(socket, 'socket', lambda *args, **kwargs: DummySocket())
    import pyvisa
    monkeypatch.setattr(pyvisa, 'ResourceManager', lambda: mock_resource_manager)

# -------------- Tests ----------------

def test_base_mw_generator_abstract_methods(monkeypatch):
    # Create a minimal concrete subclass
    class DummyGen(MicrowaveGeneratorBase):
        def set_frequency(self, hz): pass
        def set_power(self, dbm): pass
        def set_phase(self, deg): pass
    # instantiate
    gen = DummyGen(name='dummy', settings={'connection_type':'LAN','ip_address':'127.0.0.1','port':1234})
    # test send/query
    gen._send('TEST 1')
    resp = gen._query('TEST')
    assert resp == 'DUMMY_IDN'

@pytest.mark.parametrize("freq", [1e6, 2.5e9])
def test_sg384_set_and_query(freq):
    # test SG384 frequency, power, phase, output
    sg = SG384Generator(name='test_sg', settings={'connection_type':'LAN','ip_address':'127.0.0.1','port':5025})
    
    # Test that the device can be created and methods can be called
    sg.set_frequency(freq)
    sg.set_power(-10)
    sg.set_phase(45)
    sg.output_on()
    sg.output_off()
    
    # Test that settings are updated correctly
    assert sg.settings['frequency'] == freq
    assert sg.settings['amplitude'] == -10
    assert sg.settings['phase'] == 45

def test_windfreak_synthusbii_update_and_probes():
    # create instance
    usb = WindfreakSynthUSBII(name='usb', settings={'connection_type':'RS232', 'visa_resource':'ASRL9::INSTR',
                                                'ip_address':'', 'port':0,
                                                'frequency':1000.0,'power':-4,'reference':'internal',
                                                'phase_lock':'lock', 'sweep':{'freq_lower':1000.0,'freq_upper':2000.0,
                                                'freq_step':100.0,'time_step':0.3,'continuous_sweep':False,'run_sweep':False}})
    
    # Test that the device can be created and methods can be called
    usb.set_frequency(1500.0)
    usb.set_power(-4)
    usb.set_reference('internal')
    usb.set_phase_lock('lock')
    
    # Test that settings are updated correctly
    assert usb.settings['frequency'] == 1500.0
    assert usb.settings['power'] == -4
    assert usb.settings['reference'] == 'internal'
    assert usb.settings['phase_lock'] == 'lock'
    
    # Test sweep parameters
    usb.update({'sweep': {'freq_lower':1100.0,'freq_upper':1200.0,'freq_step':50.0,'time_step':0.5,'continuous_sweep':True,'run_sweep':True}})
    assert usb.settings['sweep']['freq_lower'] == 1100.0
    assert usb.settings['sweep']['freq_upper'] == 1200.0
    assert usb.settings['sweep']['continuous_sweep'] == True
