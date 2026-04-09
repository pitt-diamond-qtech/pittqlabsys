# Created by Jannet Trabelsi on 2025-08-18
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# Caution: signal levels above 30 dBm will damage the spectrum analyzer
# please note that the Dutt Lab spectrum analyzer ('GPIB0::18::INSTR') has 0 VDC MAX and 30 dBm (1W) MAX
# probe PWR provides power for high-impedance ac probes or other accessories.
# CAL out provides a calibration signal of 300 MHz at -20 dBm
# 100 MHz COMB OUT supplies a 100 MHz reference signal that has harmonics up to 22 GHz
# The box also has a memory card reader
# start freq = center freq - span/2
# stop freq = center freq + span /2
# This code's units are MHz and microseconds and dBm: to simplify problems
# Please check the min and max frequencies before running the code
# This is the Agilent8596E class, which inherits from the Device class from pittqlabsys

import pyvisa
import pyvisa.errors
import numpy as np
from src.core import Device, Parameter
import pandas as pd
from src.core.struct_hdf5 import save_parameters_hdf5, MyStruct, parameter_to_mystruct

# LIMITS
_max_freq = 12800
_min_freq = 0.009
_MAX_SET_AVG_PTS = 16384
_max_sweep_time = 100000000
_min_sweep_time_zero_span = 20
_min_sweep_time_nonzero_span = 20000
_max_span = 2943
_min_resolution_BW = 0.00003
_max_BW = 3
_min_video_BW = 0.00003
_default_sweep_time = 256000 # 1 second
_default_resolution_BW = 0.1
_default_video_BW = 1
_default_video_average = 100
_server_port = 5001
#Device._get_base_settings() +
class Agilent8596E(Device):
    _DEFAULT_SETTINGS = Parameter([
        Parameter('get_data', True, [False, True], 'choose whether you need to get data from this device or not'),
        Parameter('connection_type', 'GPIB', ['GPIB'], 'type of connection to open to controller'),
        Parameter('port', 18, list(range(0, 31)), 'GPIB port on which to connect'),
        Parameter('GPIB_num', 0, int, 'GPIB device on which to connect'),
        Parameter('center frequency', 300, float, 'center frequency'),
        Parameter('span', 0.2, float, 'span'),
        Parameter('sweep time', _default_sweep_time, float, 'sweep time'),
        Parameter('resolution band width', _default_resolution_BW, float, 'resolution band width'),
        Parameter('video band width', _default_video_BW, float, 'video band width'),
        Parameter('video average', _default_video_average, float, 'video average'),
        Parameter('server_port', _server_port, int, 'server_port'),
        ])

    def __init__(self, name=None, settings=None):
        super(Agilent8596E, self).__init__(name, settings)
        try:
            """
            # testing hdf5 save parameter
            save_parameters_hdf5(
                "agilent8596e_params.h5",
                self.settings,
                root_name="agilent8596e"
            )"""
            self._connect()
            self.agilent_analyzer.timeout = 10000  # added timeout because TS; takes longer than regular timeout
        except pyvisa.errors.VisaIOError:
            print('No Spectrum Analyzer Detected!. Check that you are using the correct communication type')
            raise
        except Exception as e:
            raise e

    def _connect(self):
        rm = pyvisa.ResourceManager()
        if self.settings['connection_type'] == 'GPIB':
            self.agilent_analyzer = rm.open_resource(
                'GPIB' + str(self.settings['GPIB_num']) + '::' + str(self.settings['port']) + '::INSTR')
            self.agilent_analyzer.write("IP;")  # initialize
            print("Agilent8596E Connected. Please note that the units are in MHz, us, and dBm")
        return 0

    def update(self, settings):
        super(Agilent8596E, self).update(settings)
        for key, value in settings.items():
            if key == 'connection_type':
                self._connect()
            elif not (key == 'port' or key == 'GPIB_num'):
                if self.settings.valid_values[
                    key] == bool:  # converts booleans, which are more natural to store for on/off, to
                    value = int(value)  # the integers used internally in the analyzer
                key = self._param_to_internal_write(key)
                # only send update to Device if connection to Device has been established
                if self._settings_initialized:
                    if key == "VAVG ":
                        self.agilent_analyzer.write(key + str(value) + ";")
                    elif key == "ST " :
                        self.agilent_analyzer.write(key + str(value) + "US;")
                    else:
                        self.agilent_analyzer.write(key + str(value) + "MZ;")

    def write(self, message):
        self.agilent_analyzer.write(message)

    @property
    def _PROBES(self):
        return {
            'get_data': 'choose whether you need to get data from this device or not',
            "center frequency": 'Center Frequency in MHz',
            "marker resolution": 'marker resolution',
            "correction values": 'correction values after set_amplitude_correction function',
            "amplitude correction length": 'amplitude correction length',
            "amplitude units": 'amplitude units',
            "marker amplitude": 'marker amplitude',
            "marker frequency": 'marker frequency',
            "trace AP": 'trace A data in float numbers',
            "trace AB": 'trace A data in binary numbers',
            "reference level amplitude": 'reference level amplitude',
            "span": 'span',
            "sweep time": 'sweep time',
            "resolution band width": 'resolution band width',
            "video band width": 'resolution band width',
            "FFT clip": 'FFT clip',
            "active marker number": 'active marker number',
            "fft percent amplitude modulation": 'fft percent amplitude modulation',
            "coupling": 'coupling',
            "id": 'id'
        }

    def read_probes(self, key):
        assert (
            self._settings_initialized)  # will cause read_probes to fail if settings (and thus also connection) not yet initialized
        assert key in list(self._PROBES.keys())
        if key == 'get_data':
            return self.settings['get_data']
        key_internal = self._param_to_internal(key)
        if key == "trace AP":
            value = self.agilent_analyzer.query(key_internal)
            return [float(val.strip()) for val in value.strip().split(',') if val.strip()]
        elif key == "trace AB":
            self.agilent_analyzer.write(key_internal)
            num_bytes = 802
            raw = self.agilent_analyzer.read_bytes(num_bytes)
            trace_raw_units = np.frombuffer(raw, dtype='>u2')
            return trace_raw_units
        elif key == "coupling":
            return self.agilent_analyzer.query(key_internal)
        return float(self.agilent_analyzer.query(key_internal))

    @property
    def is_connected(self):
        try:
            self.agilent_analyzer.query(
                "ID?;")  # arbitrary call to check connection, throws exception on failure to get response
            return True
        except pyvisa.errors.VisaIOError:
            return False

    def _param_to_internal(self, param):
        """
        Converts settings parameters to the corresponding key used for GPIB commands in the counter.
        Args:
            param: settings parameter, ex. enable_output
        Returns: GPIB command, ex. ENBR
        """
        if param == "center frequency":
            return "CF?;"
        elif param == "marker resolution":
            return "MKFCR?;"
        elif param == "correction values":
            return "AMPCOR?;"
        elif param == "amplitude correction length":
            return "AMPLEN?;"
        elif param == "amplitude units":
            return "AUNITS?;"
        elif param == "marker amplitude":
            return "MKA?;"
        elif param == "marker frequency":
            return "MKF?;"
        elif param == "trace AP" or param == "trace AB":
            return "TRA?;"
        elif param == "reference level amplitude":
            return "RL?;"
        elif param == "span":
            return "SP?;"
        elif param == "sweep time":
            return "ST?;"
        elif param == "resolution band width":
            return "RB?;"
        elif param == "video band width":
            return "VB?;"
        elif param == "FFT clip":
            return "FFTCLIP?;"
        elif param == "active marker number":
            return "MKACT?;"
        elif param == "fft percent amplitude modulation":
            return "FFTPCTAM?;"
        elif param == "coupling":
            return "COUPLE?;"
        elif param == "id":
            return "ID?;"
        else:
            print(f" cannot find param {param}")
            raise KeyError

    def _param_to_internal_write(self, param):
        if param == "center frequency":
            return ("CF ")
        elif param == "span":
            return ("SP ")
        elif param == "sweep time":
            return ("ST ")
        elif param == "resolution band width":
            return ("RB ")
        elif param == "video band width":
            return ("VB ")
        elif param == "video average":
            return ("VAVG ")

    def initialize_sa(self):
        """This function initializes the spectrum analyzer and resets the center frequency to 6400 MHz and span to 12800 MHz"""
        """
Turns off A - B mode.

Turns off A - B plus display line mode.

            Turns off amplitude correction factors.

Turns off the Analog+ display mode.

Turns on annotation.
Sets attenuation to 10 dB.

Loads the amplitude units from a configuration location in spectrum
analyzer memory.

Couples RB, AT, SS, ST, and VB.
            Turns off display line and threshold.

Blanks trace B and trace C.

Erases user graphics.

Clears and writes trace A.

Selects continuous sweep mode.

Selects ac coupling.
            (HP 85943, HP 85953, HP 85963 only.)

Sets the display address to zero.

Selects positive peak detection.

Turns off the display line.

Sets the dot density value to 15.

            Sets FM gain to 100 kHz.
            (Option 102 or 103 only.)

Sets the frequency offset to 0 Hz.

Sets the gating to off. (Option 105 only.)

Sets the gate control to edge triggering. (Option 105 only.)"""
        self.agilent_analyzer.write("IP;")

    # sweep
    def take_sweep(self):
        """A take sweep is required for each sweep in the single-sweep mode. TS prevents further input
from the interface bus until the sweep is completed to allow synchronization with other
instruments."""
        self.agilent_analyzer.write("TS;")  # take sweep

    def set_single_sweep(self):
        """Each time TS (take sweep) is sent, one sweep is initiated, as long as the trigger and data entry
conditions are met."""
        self.agilent_analyzer.write("SNGLS;")

    def set_continuous_sweep(self):
        """The CONTS command sets the spectrum analyzer to continuous sweep mode. In the continuous
sweep mode, the spectrum analyzer takes its next sweep as soon as possible after the current
sweep (as long as the trigger conditions are met). A sweep may temporarily be interrupted by
data entries made from the front panel or over the remote interface."""
        self.agilent_analyzer.write("CONTS;")

    # time is in microseconds
    def set_sweep_time(self, time_us):
        """When used as a predefined variable, ST returns the sweep time as a real number in microseconds."""
        print("current sweep time: " + str(self.get_sweep_time()))
        print("input: "+str(time_us))
        print("_min_sweep_time_nonzero_span"+str(_min_sweep_time_nonzero_span))
        print("_max_sweep_time"+str(_max_sweep_time))
        if not isinstance(time_us, (int, float)):
            raise TypeError
        span = self.get_span()
        if span == 0:
            if time_us < _min_sweep_time_zero_span or time_us > _max_sweep_time:
                raise ValueError
            else:
                time_us = str(time_us)
        else:
            if time_us < _min_sweep_time_nonzero_span or time_us > _max_sweep_time:
                raise ValueError
            else:
                time_us = str(time_us)
        self.agilent_analyzer.write("ST " + time_us + "US;")

    ## trace
    def set_trace_a(self):
        """This provides a method for returning or storing 16-bit trace values"""
        self.agilent_analyzer.write("TRA;")

    def set_trace_values(self, values):
        # Convert each value to string
        data_str = ','.join(str(v) for v in values)
        # Send string to instrument
        self.agilent_analyzer.write(data_str)

    def set_trace_data_transfer(self, data_transfer_mode):
        """Formats trace information for return to the controller."""
        """Description: TDF P is the real number format. An example of a trace element returned with
the real number format is 10.00 dB. When querying the trace or marker value, the value is
returned using the amplitude unit set by AUNITS (for example, watts or dBm)."""
        """Description: TDF A is the A-block data format. With the A-block data format, trace data is
preceded by “#, ” “A,” and a two-byte number (the two byte number indicates the number
of trace data bytes). The setting of the MDS command determines whether the trace data is
transferred as one or two g-bit bytes."""
        """Description: TDF I is the I-block data format. With the I-block data format, trace data must
be preceded by “#,” and “I.” The setting of the MDS command determines whether the trace
data is transferred as one or two g-bit bytes. Unlike using the A-block format, you do not
provide the number of data bytes when sending trace data back to the spectrum analyzer."""
        """Description: TDF B enables the binary format. With the binary format, the marker or trace
data is transferred as bytes. Of all the trace data formats, TDF B transfers trace data the
fastest. The setting of the MDS command determines whether the trace data is transferred as
one or two 8-bit bytes."""
        """Description: TDF M is the measurement data format. The measurement data format transfers
trace data in measurement units, and the measurement data can range from -32768 to
+ 32767."""
        if data_transfer_mode not in ["P", "A", "B", "I", "M"]:
            raise KeyError
        self.agilent_analyzer.write("TDF " + data_transfer_mode + ";")

    def set_meas_data_size(self, MDS="W"):
        """The MDS command formats binary data in one of the following formats:
B selects a data size of one 8-bit byte. When transferring trace data, MDS B transfers trace
data the faster than MDS W because only 401 bytes are transferred. Because MDS B
combines two bytes into one byte, some resolution is lost.
W selects a data size of one word, which is two 8-bit bytes. When transferring trace data,
MDS W transfers 802 bytes of trace data with no loss of resolution."""
        if MDS not in ["W", "B"]:
            raise KeyError
        self.agilent_analyzer.write("MDS " + MDS + ";")

    def set_trace_a_to_zero(self):
        """This sets all of trace A data to 0"""
        self.agilent_analyzer.write("MOV TRA, 0;")

    def view_trace_data(self):
        """This function stops data acquisition and displays the trace A content"""
        self.agilent_analyzer.write("VIEW TRA;")

    def display_trace_data(self):
        """This function displays Trace A data"""
        self.agilent_analyzer.write("TRDSP TRA,ON;")

    def clearwrite(self):
        """Clears the specified trace and enables trace data acquisition"""
        self.agilent_analyzer.write("CLRW;")

    # The purpose of this function is to perform a spatial video averaging as compared to the
    # temporal version supplied by the video-average (VAVG) command. The functions of SMOOTH
    # and VAVG are not interchangeable. However, unlike VAVG, SMOOTH averages values that occur
    # before and after the data point in time: use low values for the smooth parameter to avoid signal distortion
    # I do not recommend using this function if you want to keep taking data live since this function can only execute when you call self.view_trace_data(), which stops data acquisition and you have to reinitialize the device to get data again
    def smooth_trace(self, num_points):
        if isinstance(num_points, str) or isinstance(num_points, int) or isinstance(num_points, float):
            try:
                num_points = int(num_points)
                if num_points < 0:
                    raise ValueError
                num_points = str(num_points)
            except ValueError:
                raise ValueError("Wrong num_points input")
        self.agilent_analyzer.write(
            "SMOOTH TRA," + num_points + ";")  # Smoothes the trace according to the number of points specified for the running average

    def set_video_average(self, num_points):
        """perform a temporal video averaging"""
        if isinstance(num_points, str) or isinstance(num_points, int) or isinstance(num_points, float):
            try:
                num_points = int(num_points)
                if num_points < 1 or num_points > _MAX_SET_AVG_PTS:
                    raise ValueError
                num_points = str(num_points)
            except ValueError:
                raise ValueError("Wrong num_points input")
        self.agilent_analyzer.write(
            "VAVG " + num_points + ";")  # Smoothes the trace according to the number of points specified for the running average

    def stop_video_average(self):
        """stops video averaging"""
        self.agilent_analyzer.write("CLRAVG;")

    def set_center_frequency(self, frequencyMHZ):
        """sets the center frequency to the input frequency"""
        if isinstance(frequencyMHZ, str) or isinstance(frequencyMHZ, int) or isinstance(frequencyMHZ, float):
            try:
                frequencyMHZ = float(frequencyMHZ)
                if frequencyMHZ > _max_freq or frequencyMHZ < _min_freq:
                    raise ValueError("Wrong center frequency input")
            except ValueError:
                raise ValueError("Wrong center frequency input")
            self.agilent_analyzer.write('CF ' + str(frequencyMHZ) + 'MZ;')  # Specifies center frequency.

    def set_span(self, spanMHz):
        """Sets the span (span is the frequency range in the window displayed)"""
        cf = self.get_center_frequency()
        if isinstance(spanMHz, str) or isinstance(spanMHz, int) or isinstance(spanMHz, float):
            try:
                span = float(spanMHz)
                # print((cf - (span / 2)))
                if (cf - (span / 2)) < 0 or (cf + (span / 2)) > _max_freq:
                    raise ValueError
            except ValueError:
                raise ValueError("Wrong span input")
        self.agilent_analyzer.write("SP " + str(spanMHz) + "MHZ")

    def set_last_span(self):
        """sets the span to the previous span"""
        self.agilent_analyzer.write("LSPAN;")
        # Changes the spectrum analyzer's span to the previous span setting.

    def set_resolution_bw(self, RBWMHZ):
        """Sets the resolution bandwidth in MHz"""
        if isinstance(RBWMHZ, str) or isinstance(RBWMHZ, int) or isinstance(RBWMHZ, float):
            try:
                RBWMHZ = float(RBWMHZ)
            except ValueError:
                raise ValueError("Wrong RBW input")
            if RBWMHZ < _min_resolution_BW or RBWMHZ > _max_BW:
                raise ValueError("Wrong RBW input")
        self.agilent_analyzer.write("RB " + str(RBWMHZ) + "MHZ")

    def set_video_bw(self, VBWMHZ):
        """Sets the video bandwidth in MHz"""
        if isinstance(VBWMHZ, str) or isinstance(VBWMHZ, int) or isinstance(VBWMHZ, float):
            try:
                VBWMHZ = float(VBWMHZ)
            except ValueError:
                raise ValueError("Wrong VBW input")
            if VBWMHZ < _min_video_BW or VBWMHZ > _max_BW:
                raise ValueError("Wrong VBW input")
        self.agilent_analyzer.write("VB " + str(VBWMHZ) + "MHZ")

    def set_amplitude_correction(self, freq_amp_pair):
        self.agilent_analyzer.write(
            "AMPCOR " + freq_amp_pair + ";")  # example for freq_amp_pair is 100MHZ,5DB, to turn off type OFF for freq_amp_pair
        # Use AMPCOR to compensate for frequency-dependent amplitude variations at the spectrum analyzer input. Up to 79 pairs of frequency-amplitude correction points can be entered. The frequency values entered must either be equal or in increasing order, or an error condition results.

    def set_amplitude_units(self, units):
        """Sets the amplitude units: default units are dBm"""
        if units not in ["DBM", "DBMV", "DBUV", "V", "W"]:
            raise KeyError
        self.agilent_analyzer.write("AUNITS " + units + " ;")

    def set_attenuation(self, attenuationDB):
        """sets the attenuation in dB"""
        if isinstance(attenuationDB, str):
            try:
                attenuation = float(attenuationDB)
            except ValueError:
                raise ValueError("Wrong attenuation input")
            if attenuation < 10:
                raise ValueError
            self.agilent_analyzer.write("AT " + attenuationDB + "DB;")
        elif isinstance(attenuationDB, int) or isinstance(attenuationDB, float):
            if attenuationDB < 10:
                raise ValueError
            self.agilent_analyzer.write("AT " + str(attenuationDB) + "DB;")

    # marker:
    def set_marker_track(self, enable):
        """Enables marker track"""
        if enable not in ["0", "1", 0, 1]:
            raise KeyError
        elif enable in ["0", 0]:
            self.agilent_analyzer.write("MKTRACK OFF;")
        else:
            self.agilent_analyzer.write("MKTRACK ON;")

    def set_marker_frequency(self, frequency):
        """Sets the marker frequency in MHz"""
        try:
            frequency = float(frequency)
        except ValueError:
            raise ValueError("Wrong frequency input")
        if frequency < _min_freq or frequency > _max_freq:
            raise ValueError("Wrong frequency input")
        self.agilent_analyzer.write("MKF " + str(frequency) + "MHz;")

    # Moves the signal on which the active marker is located, to the center of the spectrum analyzer display and keeps the signal peak at center screen

    def set_active_marker_number(self, marker_number):
        """The spectrum analyzer has 4 markers, but only one can be active at any time. to activate, you need to input the marker number (1, 2, 3, or 4) and all the following functions that involve markers will manipulate the last marker that you activated"""
        if marker_number not in ["1", "2", "3", "4", 1, 2, 3, 4]:
            raise KeyError
        self.agilent_analyzer.write("MKACT " + str(marker_number) + ";")

    def set_marker_min(self):
        self.agilent_analyzer.write("MKMIN;")
        # Places a marker at the minimum amplitude of trace

    def set_marker_delta(self):
        self.agilent_analyzer.write("MKD;")
        # Adds a new marker called Marker Delta and puts it in the same position as the active marker
        """
        Example:
        "MKMIN;" Places a marker at the minimum amplitude of trace.
        "MKD;" Activates marker delta.
        "MKPK HI;" Places marker at highest amplitude of trace.
        "MKSP;" Changes span to the values of the left and right markers
        "sp?" read span
        This example allows us to get the frequency difference between the minimum and maximum amplitudes of the spectrum
        """

    def set_marker_span(self):
        self.agilent_analyzer.write("MKSP;")
        # Changes span to the values of the left and right markers

    def set_marker_amplitude(self, amplitude):
        """Places the marker at <amplitude> dBm."""
        if isinstance(amplitude, str):
            try:
                amp = float(amplitude)
            except ValueError:
                raise ValueError("Wrong amplitude input")
            if amp > 30:
                raise ValueError
            self.agilent_analyzer.write("MKTYPE AMP")  # Changes the marker type to amplitude.
            self.agilent_analyzer.write("MKA " + amplitude + ";")  # Places the marker at <amplitude> dBm.
        elif isinstance(amplitude, int) or isinstance(amplitude, float):
            if amplitude > 30:
                raise ValueError
            self.agilent_analyzer.write("MKTYPE AMP")  # Changes the marker type to amplitude.
            self.agilent_analyzer.write("MKA " + str(amplitude) + ";")  # Places the marker at <amplitude> dBm.

    def set_marker_resolution(self, MRinMHz):
        """Sets the marker resolution in MHz"""
        self.agilent_analyzer.write("MKFCR " + MRinMHz + "MHZ;")

    def set_marker_at_peak(self, param="HI"):
        if param not in ["HI", "NH", "NR", "NL"]:
            raise KeyError
        self.agilent_analyzer.write("MKPK " + param + ";")
        """
        These are the specific purposes for the params
        HI (highest) moves the active marker to the highest peak.
        NH (next highest) moves the active marker to the next signal peak of lower amplitude.
        NR (next right) moves the active marker to the next signal peak of higher frequency.
        NL (next left) moves the active marker to the next signal peak of lower frequency.
        """

    def move_peak_to_center(self):
        """This function moves the marker to the center of the screen"""
        self.agilent_analyzer.write("MKCF;")

    def single_FFT(self, center_frequencyMHZ=300, spanMHZ=0.2, RBWMHZ=3, sweep_time=3333, window = "FLATTOP"):
        """FFT weights the source trace with the function in the window trace. The transform is computed and the results are placed in the destination
        trace. Unlike FFTAUTO and FFTCONTS, FFT performs the FFT measurement only once. Use
        FFTAUTO or FFTCONTS if you want the FFT measurement to be performed at the end of every
        measurement sweep.
        The spectrum analyzer should be in linear mode when using the FFT command. The FFT
        results are displayed on the spectrum analyzer in logarithmic scale. For the horizontal
        dimension, the frequency on the left side of the graph is 0 Hz, and on the right side is Fmax.
        Fmax can be calculated using a few simple equations and the sweep time of the spectrum
        analyzer. The sweep time divided by the number of trace array elements containing amplitude
        information is equal to the sampling period. The reciprocal of the sampling period is the
        sampling rate. The sampling rate divided by two yields Fmax.
        For example, let the sweep time of the spectrum analyzer be 20 ms and the number of trace
        elements be 400. The sweep time (20 ms) divided by 400 equals 50 ps, the sampling period.
        The sample rate is l/50 ps. Fmax equals l/50 p.s divided by 2, or 10 kHz.
        FFT is designed to be used in transforming zero span information into the frequency domain.
        Performing FFT on a frequency sweep (when the frequency span is greater than zero) will not
        provide time-domain results.
        The windowing function stored in the window trace may be selected with the trace window
        (TWNDOW) command. You may also store your own values in that trace. The trace window
        function modifies the contents of a trace array according to one of three built-in algorithms:
        UNIFORM, HANNING, or FLATTOP
        """
        self.initialize_sa()
        self.set_single_sweep()
        self.set_center_frequency(center_frequencyMHZ)
        print("center frequency:")
        print(self.get_center_frequency())
        self.set_span(spanMHZ)
        print("span:")
        print(self.get_span())
        self.take_sweep()
        self.set_marker_at_peak("HI")
        print("Marker at peak:")
        print(self.get_marker_frequency())
        self.set_marker_track(1)
        self.set_continuous_sweep()
        self.set_resolution_bw(RBWMHZ)
        print("resolution bw:")
        print(self.get_resolution_bw())
        self.set_marker_track(0)
        self.set_span(0)
        print("span:")
        print(self.get_span())
        self.set_marker_at_peak("HI")
        print("marker freq at peak:")
        print(self.get_marker_frequency())
        self.set_marker_to_reference_level()
        self.set_linear_scale()
        self.set_single_sweep()
        self.set_sweep_time(sweep_time)
        print("sweep time:")
        print(self.get_sweep_time())
        self.take_sweep()
        self.set_trace_window(window)
        self.agilent_analyzer.write("FFT TRA,TRA,TRB;")
        self.view_trace_data()
        self.set_marker_at_peak("HI")
        self.set_marker_delta()
        self.set_marker_at_peak("NH")
        print("marker freq at NH peak:")
        print(self.get_marker_frequency())
        self.agilent_analyzer.write("MKREAD FFT;")
        print(self.get_marker_frequency())

    def continuous_sweep_FFT(self):
        """When FFTCONTS is executed, the spectrum analyzer does the following:
        - Changes to the continuous sweep mode.
        - If the current detector is the peak detector, changes to the sample detector.
        Does an FFT on trace A. Trace A is then placed in both the clear-write and store-blank
        modes. (When the spectrum analyzer is in both the clear-write and store-blank modes, the
        trace data is still taken from the spectrum analyzer input during every measurement sweep,
        but the trace is not shown on the spectrum analyzer display.)
        - Places the results in trace B (trace B is placed in the view mode).
        You can use the results of the FFTCLIP command to determine if the FFIT data is valid. If you
        want to view the input data (trace A), execute "TRDSP TRA,ON;"
        """
        self.set_span(0)
        self.set_linear_scale()
        self.agilent_analyzer.write("FFTCONTS;")

    def auto_FFT(self, center_frequency_MHz, span_MHz, sweeptime_us):
        """FFTAUTO uses the marker’s position to determine which signal is to be measured. FFTAUTO
        centers the signal and, if the frequency span of the spectrum analyzer is greater than zero,
        decreases the frequency span to zero before performing an FFT on the signal. When the FFT is
        performed, the spectrum analyzer does the following:
        n Changes to the continuous sweep mode.
        n Changes to the linear amplitude scale.
        n If the current detector is the peak detector, changes to the sample detector.
        n If the initial frequency span was greater than 0 Hz, the spectrum analyzer adjusts the signal
        peak to within 0.5 division of the top graticule.
        n Does an FFT on trace A and then places trace A in both the clear-write and store-blank
        modes. (When the spectrum analyzer is in both the clear-write and store-blank modes, the
        trace data is still taken from the spectrum analyzer input during every measurement sweep,
        but the trace is not shown on the spectrum analyzer display.)
        n Places the results of the FFT in trace B, and then changes trace B to the view mode.
        FFTAUTO performs the FFT on the signal at the end of every sweep. After executing
        FFTAUTO, you should adjust the values for the resolution bandwidth, video bandwidth,
        and sweep time according to the highest modulation frequency of interest. The resolution
        bandwidth should be about ten times greater than the highest modulation frequency of
        interest, and the video bandwidth should be about 10 times higher than the highest modulation
        frequency of interest"""
        self.agilent_analyzer.write("RL 0DB;")
        self.set_center_frequency(center_frequency_MHz)
        self.set_span(span_MHz)
        self.set_marker_at_peak("HI")
        print("marker frequency:")
        print(self.get_marker_frequency())
        self.agilent_analyzer.write("FFTAUTO;")
        self.set_sweep_time(sweeptime_us)
        print("sweep time:")
        print(self.get_sweep_time())
        print("center frequency:")
        print(self.get_center_frequency())
        print("span:")
        print(self.get_span())
        print("marker frequency:")
        print(self.get_marker_frequency())

    def FFT_CLIP(self):
        """Indicates if the FFT results are valid: if the output is 0 then not clipped, and if the output is 1 then clipped"""
        return self.read_probes("FFT clip")

    def FFT_marker_to_midscreen(self):
        """FFTMM is performed only if the spectrum analyzer is performing an FFT measurement.
        Changing the FFT midscreen frequency of the spectrum analyzer also changes the FFT stop
        frequency of the spectrum analyzer. Because the FFT stop frequency is limited by sweep time
        of the spectrum analyzer, it may not be possible to change the FFT midscreen frequency to the
        frequency of the FFT marker. If the FFTMM command does not move the signal to the FFT
        midscreen frequency, you should check if the FFT stop frequency is limited by the sweep time
        range or the sweep time increments for your spectrum analyzer. The FFT stop frequency is
        related to the sweep time as follows: FFTSTOPFREQ = 400/ (2*sweep time)"""
        """Example: FFTCONTS; MKPK HI; MKPK NH; FFTMM"""
        self.agilent_analyzer.write("FFTMM;")

    def FFT_marker_to_FFT_stop_frequency(self):
        """FFTMS is performed only if the spectrum analyzer is performing a FFT measurement. If a
        marker is on a signal, FFTMS will move that signal to the right side of the graticule. FFI’MS
        is useful because moving the signal toward the FFT stop frequency increases the frequency
        resolution of the FF”I’ measurement. For best results, the signal of interest should be placed
        slightly left of the FFI’ stop frequency (the signal should not touch the right side of the
        graticule). If the signal is placed at the FFT stop frequency, small variations in acquired data
        can cause large changes in the displayed amplitude of the signal which do not reflect the actual
        signal amplitude.
        Because the FFT stop frequency is limited by sweep time of the spectrum analyzer, it may not
        be possible to change the FFT midscreen frequency to the frequency of the FFT marker. If
        the FFTMS command does not move the signal to the FYI’ stop frequency, you should check if
        the FFT stop frequency is limited by the sweep time range or sweep time increments for your
        spectrum analyzer. The FFT stop frequency is related to the sweep time as follows: FFTSTOPFREQ = 400/ (2*sweep time)"""
        """example: FFTCONTS; MKPK NH; FFTMS"""
        self.agilent_analyzer.write("FFTMS;")

    def FFT_OFF(self):
        """The FFTOFF command aborts any of the FFT functions (FFTAUTO, FFTCONTS, FFTMKR, or
        FFTSNGLS) and returns the spectrum analyzer display back to normal"""
        self.agilent_analyzer.write("FFTOFF")

    def set_FFT_percent_amplitude_modulation(self, enable):
        """The FFTPCTAM command turns the percent AM function on or off. The percent AM
        modulation is calculated using only the largest single frequency of modulation.
        FFTPCTAM can be executed on FFT trace data even if an FFT measurement is not being
        performed, as long as the FFT marker (FFTMKR) is invoked. For example, you can restore the
        percent AM readout of a recalled FFT trace by executing the FFTMKR command, and then the
        FFTPCTAM command.
        You can execute the FFTPCTAM command two different ways. You can either execute the
        FFTPCTAM command directly (for example, "FFTPCTAM 1;") or use the MOV command to move
        the 1 or 0 into the FFTPCTAM command (for example, "MOV FFTPCTAM,1;"). If you use the
        MOV command, no text is displayed in the active function area during command execution"""
        """example: FFTCONTS; MOV FFTPCTAM, 1;"""
        if enable not in [0, 1, "0", "1"]:
            raise KeyError
        self.agilent_analyzer.write("MOV FFTPCTAM," + str(enable) + ";")

    def get_FFT_percent_amplitude_modulation(self):
        return self.read_probes("fft percent amplitude modulation")

    def set_marker_to_reference_level(self):
        self.agilent_analyzer.write("MKRL")

    def set_trace_window(self, selection="FLATTOP"):
        """Selecting a window: The amplitude and frequency uncertainty of the Fourier-transformed
        display depends on both the choice of trace windows and the spectrum analyzer sweep time.
        Passbands that are flatter in shape, like the FLATTOP filter, contribute less
        amplitude uncertainty, but frequency resolution and sensitivity are compromised. The FLATTOP window has the greatest frequency uncertainty of the windows, but it has
        outstanding side lobe suppression and amplitude flatness. Use FLATTOP to transform periodic signals.
        The UNIFORM window algorithm has the least frequency uncertainty and greatest amplitude
        uncertainty.
        The UNIFORM window does not contain time-domain weighing and leaves the
        data alone. Use the UNIFORM window for transforming noise signals or transients that decay
        within one sweep time period. The UNIFORM window yields the best frequency resolution, but
        also produces the highest side lobes for periodic signals.
        The HANNING window is a traditional passband window found in most real-time spectrum
        analyzers. The HANNING window offers a compromise between the FLATTOP and UNIFORM
        windows. Use the HANNING window when transforming periodic or random data.
        The values in the window trace range from -32,768 to 32,767 and are treated as fractional
        numbers. No offset is used. When FFT is called, the average window value is computed and
        used to correct the results in absolute units.
        When the source is longer than the destination, the source is truncated to fit. When the source
        is shorter than the destination, the last element is repeated to fill the destination.
        """
        # creates a window trace array for the FFT function
        if selection not in ["FLATTOP", "UNIFORM", "HANNING"]:
            raise KeyError
        self.agilent_analyzer.write("TWNDOW TRB," + selection + ";")

    def set_linear_scale(self):
        self.agilent_analyzer.write("LN")

    def set_analog_plus(self, EN):
        if EN not in ["ON", "OFF"]:
            raise KeyError
        self.agilent_analyzer.write("ANLGPLUS " + EN + ";")  # EN can only be ON or OFF
        # The Analog+ display mode enables the trace display to emulate an analog display. Emulating an analog display means that a dot density of up to 40 dots per trace element can be obtained instead of the usual one point per trace element.

    def set_average(self, ratio):
        if isinstance(ratio, str):
            try:
                r = int(ratio)
            except ValueError:
                raise ValueError("wrong ratio input")
            if r < 0 or r == 0:
                raise ValueError
        elif isinstance(ratio, int):
            if ratio < 0 or ratio == 0:
                raise ValueError
            ratio = str(ratio)
        else:
            raise KeyError
        self.agilent_analyzer.write(
            "AVG TRA,TRB," + ratio + ";")  # Averages traces B and A with ratio and store the result in trace A

    def get_resolution_bw(self):
        return self.read_probes("resolution band width") / 1000000

    def get_video_bw(self):
        return self.read_probes("video band width") / 1000000

    # time is in microseconds
    def get_sweep_time(self):
        return self.read_probes("sweep time") * 1000000

    # center frequency is in MHz
    def get_center_frequency(self):
        return self.read_probes("center frequency") / 1000000

    def get_span(self):
        return self.read_probes("span") / 1000000

    def get_amplitude_correction_vals(self):
        return self.read_probes("correction values")

    # after using set_amplitude_correction function

    def get_amplitude_correction_length(self):
        return self.read_probes("amplitude correction length")

    # The absolute value of the number that AMPLEN? returns is the number of frequency amplitude correction factors that have been entered. If no amplitude correction factors have been entered, AMPLEN? returns a 0.

    def get_amplitude_units(self):
        return self.read_probes("amplitude units")

    def get_active_marker_number(self):
        return self.read_probes("active marker number")

    def get_marker_resolution(self):
        return self.read_probes("marker resolution")

    def get_marker_amplitude(self):
        return self.read_probes("marker amplitude")  # this will be in dBm

    def get_marker_frequency(self):
        return self.read_probes("marker frequency") / 1000000  # this will be in MHz

    def get_trace_a_data(self, data_transfer_mode):
        if data_transfer_mode not in ["P", "A", "B", "I", "M"]:
            raise KeyError
        # self.agilent_analyzer.write("TDF "+data_transfer_mode+";")
        if data_transfer_mode == "P":
            return self.read_probes("trace AP")  # gives us data in dBm
        else:
            return self.read_probes("trace AB")

    def get_reference_level_amplitude(self):
        return self.read_probes("reference level amplitude")

    def get_coupling(self):
        return self.read_probes("coupling")

    def convert_dBm_to_measurement_units(self, trace_data):
        ref_level = self.get_reference_level_amplitude()
        return (((trace_data - ref_level) * 100) + 8000).astype(int)

    def convert_measurement_units_to_dBm(self, trace_data):
        ref_level = self.get_reference_level_amplitude()
        return ((trace_data - 8000) * 0.01) + ref_level

    def maniputale_RES_BW(self, frequencyMHZ):
        if isinstance(frequencyMHZ, str):
            try:
                frequency = float(frequencyMHZ)
            except ValueError:
                raise ValueError("Wrong frequency input")
            if frequency > _max_freq or frequency < _min_freq:
                raise ValueError
        elif isinstance(frequencyMHZ, int) or isinstance(frequencyMHZ, float):
            if frequencyMHZ < 0 or frequencyMHZ > _max_freq or frequencyMHZ < _min_freq:
                raise ValueError
            frequencyMHZ = str(frequencyMHZ)
        self.agilent_analyzer.write("ACTDEF M-BW,%MY BANDWIDTH%," + frequencyMHZ + "MHZ,STEP,@")
        # Defines a function called M-BW which allows manipulation of the initial value of RES BW (MHz) by the step keys and the knob. The resolution bandwidth will be rounded to the nearest allowable bandwidth, however The “@” symbol marks the end of the ACTDEF declaration
        self.agilent_analyzer.write("MOV RB,M_BW@;")
        self.agilent_analyzer.write("M_BW;")  # Activates the M-BW function.
        A = self.agilent_analyzer.query("ACTDEF M_BW?;")  # Queries the definition of the M-BW function.
        return A

    def get_data(self):
        """ this is overriding the function in the parent device class to include self.data.trace as it is not present in the parameters"""
        self.data = MyStruct()
        self.data.params = parameter_to_mystruct(self.settings)
        self.data.trace = np.array(self.read_probes("trace AP"))
        return self.data


if __name__ == '__main__':
    ag = Agilent8596E()
    ag.update({'span': 300})

    # TESTS RAN SUCCESSFULLY:
    # first test: PAGE 52: Successful
    """
    #ag.set_trace_a()
    ag.initialize_sa()
    ag.set_center_frequency("300")
    ag.set_single_sweep()
    ag.take_sweep()
    print(ag.get_center_frequency())
    #ag.set_trace_data_transfer("P")
    ag.set_single_sweep()
    ag.take_sweep()
    ag.set_marker_frequency(300)
    print("marker freq at center freq:")
    print(ag.get_marker_frequency())
    print("marker amp at center frequency")
    print(ag.get_marker_amplitude())
    ag.set_marker_at_peak()
    #ag.move_peak_to_center()
    print("marker amp at peak")
    print(ag.get_marker_amplitude())
    print("marker freq at peak")
    print(ag.get_marker_frequency())
    ag.set_continuous_sweep()
    """

    # TDF P example: Page 75:  Successful
    """
    ag.set_center_frequency(300)
    ag.set_span(20)
    ag.set_single_sweep()
    ag.take_sweep()
    trace_data = np.array(ag.get_trace_a_data("P"))
    print(trace_data)
    ag.view_trace_data()
    ag.set_trace_a_to_zero()
    refl=ag.get_reference_level_amplitude()
    print(refl)
    values = ag.convert_dBm_to_measurement_units(trace_data)
    print(values)
    ag.set_trace_a()
    ag.set_trace_values(values)
    """

    # TDF B example: Page 76: Successful
    """
    ag.set_center_frequency(300)
    ag.set_span(20)
    ag.set_single_sweep()
    ag.take_sweep()
    ag.set_meas_data_size()
    trace_data = np.array(ag.get_trace_a_data("B"))
    print(trace_data)
    ag.set_trace_data_transfer("A")
    ag.set_trace_a_to_zero()
    ag.set_trace_a()
    ag.set_trace_values(trace_data.astype(np.int16))
    ag.view_trace_data()
    """

    # test: PAGE 56: Successful
    """
    ag.initialize_sa()
    ag.set_trace_data_transfer("P")
    ag.set_single_sweep()
    ag.set_center_frequency(300)
    ag.set_span(200)
    ag.take_sweep()
    ag.set_marker_at_peak()
    ag.move_peak_to_center()
    print(ag.get_marker_amplitude())
    print(ag.get_marker_frequency())
    print(ag.get_center_frequency())
    ag.take_sweep()
    trace_data = np.array(ag.get_trace_a_data("P"))
    ag.set_continuous_sweep()
    """

    # test: PAGE 58: save data to file + plot amplitude vs frequency: Successful
    """
    ag.initialize_sa()
    ag.set_trace_data_transfer("P")
    ag.set_single_sweep()
    ag.set_center_frequency(2500)
    span = 2000
    ag.set_span(span)
    ag.take_sweep()
    ag.view_trace_data()
    ag.smooth_trace(10)
    #ag.view_trace_data()
    ag.set_marker_at_peak()
    #ag.move_peak_to_center()
    print(ag.get_marker_amplitude())
    print(ag.get_marker_frequency())
    print(ag.get_center_frequency())
    ag.take_sweep()
    trace_data = np.array(ag.get_trace_a_data("P"))
    num_points = len(trace_data)
    center_freq = ag.get_center_frequency()
    print(center_freq)
    start_freq = center_freq - (span / 2)
    stop_freq = center_freq + (span / 2)
    freqs = np.linspace(start_freq, stop_freq, num_points)
    df = pd.DataFrame({
        'Frequency_MHz': freqs,
        'Amplitude_dBm': trace_data
    })

    df.to_csv("spectrum_data.csv", index=False)
    ag.set_continuous_sweep()
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtWidgets
    import sys

    app = QtWidgets.QApplication(sys.argv)

    win = pg.GraphicsLayoutWidget(title="Spectrum Analyzer Trace")
    plot = win.addPlot(title="Amplitude VS Frequency")
    plot.plot(freqs, trace_data, pen='y')  # Yellow line

    plot.setLabel('left', "Amplitude", units='dBm')
    plot.setLabel('bottom', "Frequency", units='MHz')
    plot.showGrid(x=True, y=True)

    win.show()
    sys.exit(app.exec_())
    """

    """
    ag.initialize_sa()
    ag.set_center_frequency(30)
    ag.set_resolution_bw(0.00003)
    print(ag.get_resolution_bw())
    ag.set_span(0)
    ag.set_sweep_time(20)
    print(ag.get_sweep_time())
    print(ag.get_span())
    """

    """
    ag.initialize_sa()
    ag.set_center_frequency("300")
    ag.set_span(0.2)
    print(ag.get_center_frequency())
    # ag.set_trace_data_transfer("P")
    ag.set_single_sweep()
    ag.take_sweep()
    #ag.set_marker_frequency(300)
    #print("marker at center freq")
    ag.set_marker_at_peak("HI")
    print("marker freq at peak")
    print(f"{ag.get_marker_frequency():.10f}")
    ag.set_marker_at_peak("NH")
    print("marker freq at NH peak")
    print(f"{ag.get_marker_frequency():.10f}")
    ag.set_marker_at_peak("NH")
    print("marker freq at NH peak")
    print(f"{ag.get_marker_frequency():.10f}")
    """
    """
    ag.set_center_frequency(300)
    ag.set_span(0.2)
    """
    # FFT TESTS:
    #"""
    #ag.initialize_sa()
    #ag.single_FFT()
    #"""
    #ag.initialize_sa()
    #ag.auto_FFT(300, 0.2, 11111)
    #ag.continuous_sweep_FFT()
    #print(ag.FFT_CLIP())
    #print(ag.get_coupling())
    print('done')