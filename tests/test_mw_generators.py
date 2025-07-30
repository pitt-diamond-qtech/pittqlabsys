# Created by gurudevdutt at 7/30/25
import pytest
import builtins
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

class DummyVisaResource:
    def __init__(self):
        self.written = []
    def write(self, cmd):
        self.written.append(cmd)
    def query(self, cmd):
        return "DUMMY_IDN\n"
    def close(self):
        pass

class DummyResourceManager:
    def open_resource(self, res):
        return DummyVisaResource()

# Monkeypatch socket and pyvisa
@pytest.fixture(autouse=True)
def patch_transports(monkeypatch):
    import socket
    monkeypatch.setattr(socket, 'socket', lambda *args, **kwargs: DummySocket())
    import pyvisa
    monkeypatch.setattr(pyvisa, 'ResourceManager', lambda: DummyResourceManager())

# -------------- Tests ----------------

def test_base_mw_generator_abstract_methods(monkeypatch):
    # Create a minimal concrete subclass
    class DummyGen(MicrowaveGeneratorBase):
        def set_frequency(self, hz): pass
        def set_power(self, dbm): pass
        def set_phase(self, deg): pass
    # instantiate
    gen = DummyGen(name='dummy', settings={'connection_type':'LAN','ip_address':'127.0.0.1','port':1234,'gpib_address':''})
    # test send/query
    gen._send('TEST 1')
    resp = gen._query('TEST')
    assert resp == 'DUMMY_IDN'

@pytest.mark.parametrize("freq", [1e6, 2.5e9])
def test_sg384_set_and_query(freq):
    # test SG384 frequency, power, phase, output
    sg = SG384Generator(connection_type='LAN', address={'ip':'127.0.0.1','port':5025})
    sg.set_frequency(freq)
    # underlying socket captured data
    sock = sg.sock
    assert any(str(freq).encode() in msg for msg in sock.sent)
    sg.set_power(-10)
    assert any(b'POWR -10DBM' in msg for msg in sock.sent)
    sg.set_phase(45)
    assert any(b'PHAS 45DEG' in msg for msg in sock.sent)
    # test output on/off
    sg.output_on()
    assert any(b'OUTP ON' in msg for msg in sock.sent)
    sg.output_off()
    assert any(b'OUTP OFF' in msg for msg in sock.sent)

def test_windfreak_synthusbii_update_and_probes():
    # create instance
    usb = WindfreakSynthUSBII(name='usb', settings={'connection_type':'RS232', 'gpib_address':'ASRL9::INSTR',
                                                'ip_address':'', 'port':0,
                                                'frequency':1000.0,'power':-4,'reference':'internal',
                                                'phase_lock':'lock', 'sweep':{'freq_lower':1000.0,'freq_upper':2000.0,
                                                'freq_step':100.0,'time_step':0.3,'continuous_sweep':False,'run_sweep':False}})
    # test frequency set
    usb.set_frequency(1500.0)
    inst = usb._inst
    assert any('f1500.0' in cmd for cmd in inst.written)
    # test probes
    val = usb.read_probes('frequency')
    assert isinstance(val, float)
    val = usb.read_probes('power')
    assert val in (-4, -1, 2, 5)
    val = usb.read_probes('reference')
    assert val in ('internal','external')
    # sweep set + run
    usb.update({'sweep': {'freq_lower':1100.0,'freq_upper':1200.0,'freq_step':50.0,'time_step':0.5,'continuous_sweep':True,'run_sweep':True}})
    # commands logged
    assert any('l1100.0' in cmd for cmd in inst.written)
    assert any('g1' in cmd for cmd in inst.written)
```}
