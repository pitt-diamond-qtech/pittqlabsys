# Created by Abby Bakkenist <gdutt@pitt.edu> on 2024-09-26
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

from src.core import Device, Parameter
import numpy as np
from ctypes import cdll, c_char_p, c_double, c_uint, c_int

# constants defined by spincore
_PULSE_PROGRAM = 0
_CONTINUE = 0
_STOP = 1
_LOOP = 2
_END_LOOP = 3
_LONG_DELAY = 7
_BRANCH = 6
_ALL_FLAGS_ON = 0x1FFFFF
_ON = 0xE00000
_ONE_PERIOD = 0x200000
_TWO_PERIOD = 0x400000
_THREE_PERIOD = 0x600000
_FOUR_PERIOD = 0x800000
_FIVE_PERIOD = 0xA00000
_SIX_PERIOD = 0xC00000
_CHANNELS = 21


class PulseBlaster(Device):
    """This class creates a SpinCorePulseBlaster object. This class initalizes the board, sends
    instructions to it, starts/stops the sequence, closes the board, etc.
    """

    _DEFAULT_SETTINGS = Parameter([
        Parameter('clock_frequency', 400e6, float, 'clock frequency (Hz)', units="Hz"),
        Parameter('min_pulse', 2.5e-6, float, 'shortest pulse (s)', units="s"),
        Parameter('max_pulse', 1.123e7, float, 'longest pulse (s)', units="s"),
        Parameter('min_interval', 1.5e-7, float, 'shortest interval (s)', units='s'),
        Parameter('max_interval', 1.123e7, float, 'longest pulse (s)', units="s"),
        Parameter('instructions', 4096, float, 'number of instructions')
    ])

    def __init__(self, name=None, settings=None, library_file='spinapi64.dll', library_header='spinapi.h'):
        self.libraryFile = library_file
        self.libraryHeader = library_header

        try:
            self._dll = cdll.LoadLibrary(library_file)
            super(PulseBlaster, self).__init__(name, settings)
            self._is_connected = True  # DLL loaded successfully
        except OSError:
            self._is_connected = False
            raise
    
    @property
    def is_connected(self) -> bool:
        """Check if the PulseBlaster device is connected and accessible."""
        if not self._is_connected:
            return False
        try:
            # Test actual connection by trying to get board status
            status = self._dll.pb_get_status()
            return True
        except Exception:
            self._is_connected = False
            return False

    # Check if the command has given an error. If so, print and return the error's description.
    def chk(self, error):
        self._dll.pb_get_error.restype = c_char_p
        recent_error = self._dll.pb_get_error()
        if error != 0:
            print(recent_error)
            return recent_error
        else:
            return None

    # Initialize the PB board.
    def init(self):
        return self.chk(self._dll.pb_init())

    # Set the clock of the PB board. NOTE: This does not actually set the clock of the PB board. The PB board must
    # be told what its frequency is. set_clock() must be called after init()
    def set_clock(self, clock_rate):
        # newer version of spinapi uses function pb_core_clock, older versions use pb_set_clock
        #  or set_clock, need to write a more compatible function here.
        try:
            getattr(self._dll, 'pb_core_clock')
        except (AttributeError, NameError):
            return self.chk(self._dll.pb_set_clock(c_double(clock_rate)))
            # print 'pb set clock loaded'
        else:
            return self.chk(self._dll.pb_core_clock(c_double(clock_rate)))
            # print 'pb core clock loaded'

    # Start programming the PB board.
    def start_programming(self):
        try:
            getattr(self._dll, 'pb_start_programming')
        except (AttributeError, NameError):
            return self.chk(self._dll.start_programming(self._PULSE_PROGRAM))
            # print 'start programming loaded'
        else:
            return self.chk(self._dll.pb_start_programming(self._PULSE_PROGRAM))
            # print 'pb start programming loaded'

    # Send instructions to the PB board.
    # returns address of current instruction to be used for branching. returns negative number in case of failed instruction
    def send_instruction(self, flags, inst, inst_data, length):
        try:
            getattr(self._dll, 'pb_inst_pbonly')
        except (AttributeError, NameError):
            print('Function pb_inst_pbonly not found.')
        else:
            address = self._dll.pb_inst_pbonly(c_uint(flags), c_int(inst), c_int(inst_data),
                                               c_double(length))
            return address

    # Stop programming the PB board.
    def stop_programming(self):
        try:
            getattr(self._dll, 'pb_stop_programming')
        except (AttributeError, NameError):
            return self.chk(self._dll.stop_programming(self._PULSE_PROGRAM))
        else:
            return self.chk(self._dll.pb_stop_programming(self._PULSE_PROGRAM))

    # Stop the pulse sequence. Note that stop() or reset() must be called before start()
    def stop(self):
        return self.chk(self._dll.pb_stop())

    def reset(self):
        return self.chk(self._dll.pb_reset())

    # Start the pulse sequence.
    def start(self):
        return self.chk(self._dll.pb_start())

    # Get the current version of SpinAPI being used by the board.
    # not currently working.
    def get_version(self):
        self._dll.pb_get_version.restype = c_char_p
        return self._dll.pb_get_version()

    # Get the current status of the board. The status functiong provided by the spinapi .dll file
    # returns a series of bits that can be translated into english.
    def status(self):
        result = ''.join(list(bin(self._dll.pb_read_status()))[2:])
        if len(result) < 4:
            result = result.zfill(4)
        result = list(result)
        status = ''
        if len(result) == 4:
            if result[-1] == '1':
                status += 'Stopped '
            if result[-2] == '1':
                status += 'Reset '
            if result[-3] == '1':
                status += 'Running '
            if result[-4] == '1':
                status += 'Waiting'
            return status
        else:
            return 'Status not understood'

    def close(self):
        return self.chk(self._dll.pb_close())


class PulseTrain(PulseBlaster):
    """This class creates PulseTrains, which belong to a PulseChannel. This class inherits basic
    functionality from PulseBlaster.
    """

    _DEFAULT_SETTINGS = Parameter([
        Parameter('clock_frequency', 400e6, float, 'clock frequency (Hz)', units="Hz"),
        Parameter('min_pulse', 2.5e-6, float, 'shortest pulse (s)', units="s"),
        Parameter('max_pulse', 1.123e7, float, 'longest pulse (s)', units="s"),
        Parameter('min_interval', 1.5e-7, float, 'shortest interval (s)', units='s'),
        Parameter('max_interval', 1.123e7, float, 'longest pulse (s)', units="s"),
        Parameter('instructions', 4096, float, 'number of instructions')
    ])

    def __init__(self, name=None, settings=None, time_on=1e-6, width=1e-7, separation=0.0, pulses_in_train=1, pulse_train_index=0):
        super(PulseBlaster, self).__init__(name, settings)  # added call to parent __init__
        self.time_on = time_on
        self.width = round(width, 10)
        self.separation = separation
        self.pulses_in_train = pulses_in_train
        self.pulse_on_times = []
        if self.pulses_in_train == 1 or self.pulses_in_train == 0:
            self.separation = 0.0
        for i in range(int(pulses_in_train)):
            self.pulse_on_times.append(round(time_on + i * (self.width + self.separation), 10))
        self.pulse_widths = [width] * int(pulses_in_train)

        self.latest_pulse_train_event = np.amax(np.array(self.pulse_on_times)) + width
        self.first_pulse_train_event = np.amin(np.array(self.pulse_on_times))


class PulseChannel(PulseTrain):
    """This class creates Pulse Channel objects, which contains PulseTrains. This class inherits basic
    functionality from PulseTrain and PulseBlaster.
    """

    _DEFAULT_SETTINGS = Parameter([
        Parameter('clock_frequency', 400e6, float, 'clock frequency (Hz)', units="Hz"),
        Parameter('min_pulse', 2.5e-6, float, 'shortest pulse (s)', units="s"),
        Parameter('max_pulse', 1.123e7, float, 'longest pulse (s)', units="s"),
        Parameter('min_interval', 1.5e-7, float, 'shortest interval (s)', units='s'),
        Parameter('max_interval', 1.123e7, float, 'longest pulse (s)', units="s"),
        Parameter('instructions', 4096, float, 'number of instructions')
    ])

    def __init__(self, name=None, settings=None, num_of_pulse_trains=0, delay_on=0.0, delay_off=0.0, pulse_channel_index=0):
        super(PulseTrain, self).__init__(name, settings)  # added call to parent __init__
        self.num_pulses = 0
        self.delay_on = delay_on
        self.delay_off = delay_off
        self.num_of_pulse_trains = num_of_pulse_trains
        self.pulse_trains = []
        self.pulse_channel_index = pulse_channel_index
        self.latest_channel_event = 0
        self.first_channel_event = 0

    def add_pulse_train(self, time_on=1e-6, width=1e-7, separation=0.0, pulses_in_train=1):
        # add this pulse to the current pulse channel
        self.num_of_pulse_trains += 1
        if self.num_of_pulse_trains != 1:
            pulse_train = PulseTrain(time_on=time_on, width=width, separation=separation,
                                     pulses_in_train=pulses_in_train)
        else:
            pulse_train = PulseTrain(time_on=time_on, width=width, separation=separation,
                                     pulses_in_train=pulses_in_train)
        self.pulse_trains.append(pulse_train)
        self.num_pulses += int(pulse_train.pulses_in_train)
        self.setLatestChannelEvent()
        self.setFirstChannelEvent()

    def delete_pulse_train(self, index):
        if self.num_of_pulse_trains > 0:
            pulse_train = self.pulse_trains.pop(index)
            self.num_of_pulse_trains -= 1
            self.setLatestChannelEvent()
            self.setFirstChannelEvent()
            return True
        else:
            return False

    # Check if any two pulses begin or end at the same time (this should not happen)
    def has_coincident_events(self):
        found_coincident_event = False
        pulse_on_times = []
        pulse_off_times = []
        for pulse_train in self.pulse_trains:
            pulse_on_times.extend(pulse_train.pulse_on_times)
        if len(pulse_on_times) > len(set(pulse_on_times)):
            found_coincident_event = True
        return found_coincident_event

    def set_first_channel_event(self):
        if self.num_of_pulse_trains > 1:
            self.first_channel_event = sorted(self.pulse_trains, key=lambda x: x.first_pulse_train_event)[
                0].first_pulse_train_event
        elif self.num_of_pulse_trains == 1:
            self.first_channel_event = self.pulse_trains[0].first_pulse_train_event
        else:
            self.first_channel_event = 0

    def set_latest_channel_event(self):
        self.latest_channel_event = 0
        for i in range(self.num_of_pulse_trains):
            if self.pulse_trains[i].latest_pulse_train_event > self.latest_channel_event:
                self.latest_channel_event = self.pulse_trains[i].latest_pulse_train_event


class PulseSequence(PulseChannel):
    """This class creates a Pulse Sequence, which contains PulseChannels. A PulseSequence object has the ability to
    add, remove, or edit thePulseTrains that belong to a PulseChannel. It can also convert the user-created
    PulseSequence (created via the PulseSequenceUI gui) into instructions for the PulseBlaster. This class inherits
    basic functionality from PulseTrain and PulseChannel.
    """

    _DEFAULT_SETTINGS = Parameter([
        Parameter('clock_frequency', 400e6, float, 'clock frequency (Hz)', units="Hz"),
        Parameter('min_pulse', 2.5e-6, float, 'shortest pulse (s)', units="s"),
        Parameter('max_pulse', 1.123e7, float, 'longest pulse (s)', units="s"),
        Parameter('min_interval', 1.5e-7, float, 'shortest interval (s)', units='s'),
        Parameter('max_interval', 1.123e7, float, 'longest pulse (s)', units="s"),
        Parameter('instructions', 4096, float, 'number of instructions')
    ])

    def __init__(self, name=None, settings=None, num_of_channels=0):
        super(PulseChannel, self).__init__(name, settings)  # added call to parent __init__
        self.num_of_channels = num_of_channels
        self.num_of_wait_events = 0
        self.channels = []
        self.pulse_channel_indices = []
        self.wait_events = []
        # latest_sequence_event is the last time that a channel is turned off
        self.latest_sequence_event = 0
        self.first_sequence_event = 0

    def add_channel(self):
        self.num_of_channels += 1
        if self.num_of_channels != 1:
            channel = PulseChannel(pulse_channel_index=self.channels[-1].pulse_channel_index + 1)
        else:
            channel = PulseChannel()
        self.channels.append(channel)
        self.pulse_channel_indices.append(channel.pulse_channel_index)
        self.setLatestSequenceEvent()
        self.setFirstSequenceEvent()

    def delete_channel(self, index):
        if self.num_of_channels > 0:
            self.channels.pop(index)
            self.num_of_channels -= 1
            self.pulse_channel_indices.pop(index)
            self.setLatestSequenceEvent()
            self.setFirstSequenceEvent()
            return True
        else:
            return False

    def add_wait_event(self, time):
        self.wait_events.append(time)
        self.num_of_wait_events += 1
        self.wait_events.sort()
        self.setLatestSequenceEvent()
        self.setFirstSequenceEvent()

    def delete_wait_event(self, index):
        self.wait_events.pop(index)
        self.num_of_wait_events -= 1
        self.wait_events.sort()
        self.setLatestSequenceEvent()
        self.setFirstSequenceEvent()

    # Return the first event of the sequence, which is either a wait event or the beginning of the first pulse(s).
    def get_first_sequence_event(self):
        self.setFirstSequenceEvent()
        return self.first_sequence_event

    # Determine the first event of the sequence.
    def set_first_sequence_event(self):
        if self.num_of_channels > 1:
            temp_channels = []
            for channel in self.channels:
                channel.setFirstChannelEvent()
                if channel.num_of_pulse_trains > 0:
                    temp_channels.append(channel)
            #    if channel.first_channel_event < self.first_sequence_event:
            #        self.first_sequence_event = channel.first_channel_event
            if len(temp_channels) > 0:
                self.first_sequence_event = sorted(temp_channels, key=lambda x: x.first_channel_event)[
                    0].first_channel_event
            else:
                self.first_sequence_event = 0
        if self.num_of_wait_events > 0:
            if float(self.wait_events[0]) < self.first_sequence_event:
                self.first_sequence_event = float(self.wait_events[0])

    def set_latest_sequence_event(self):
        self.latest_sequence_event = 0
        for i in range(self.num_of_channels):
            if self.channels[i].latest_channel_event > self.latest_sequence_event:
                self.latest_sequence_event = self.channels[i].latest_channel_event
        if self.num_of_wait_events > 0:
            if float(self.wait_events[-1]) > self.latest_sequence_event:
                self.latest_sequence_event = float(self.wait_events[-1])

    # Convert the PulseSequence to instructions for the PulseBlaster. This function will return:
    #   - a list of PulseBlaster instructions
    #   - a list of the instructions in readable form
    #   - the run-time of the sequence (specified by the user in the case of an infinite loop, or determined
    #       by the time it takes the sequence to repeat 'n' times in the case of the user choosing 'n'
    #       number of loops)
    #   - whether or not the sequence contains a bad instruction (a boolean value, will be
    #       true if the PulseBlaster is not capable of outputting the user-created pulse sequence).
    def convert_sequence_to_instructions(self, inf_loop, num_of_loops):
        self.setFirstSequenceEvent()
        self.setLatestSequenceEvent()
        # Create the event - an event occurs when a channel is turned on or off.
        channel_events = []
        for channel in self.channels:
            pulse_on_times = []
            pulse_widths = []
            for i in range(channel.num_of_pulse_trains):
                pulse_on_times += channel.pulse_trains[i].pulse_on_times
                pulse_widths += channel.pulse_trains[i].pulse_widths
            num_of_channel_events = len(pulse_on_times) * 2
            channel_event_times = np.zeros(num_of_channel_events)
            channel_event_flags = np.zeros(num_of_channel_events)
            for i in range(num_of_channel_events / 2):
                channel_event_times[2 * i] = pulse_on_times[i]
                channel_event_flags[2 * i] = 1
                channel_event_times[2 * i + 1] = pulse_on_times[i] + pulse_widths[i]
                channel_event_flags[2 * i + 1] = 0
            channel_events.append([channel_event_times, channel_event_flags, channel.pulse_channel_index])

        times = []
        for i in range(self.num_of_channels):
            times.append(channel_events[i][0])
        times = np.concatenate(times)

        # Get unique event times to eliminate coincident events.
        unique_event_times, unique_indices = np.unique(times, return_index=True)
        num_of_unique_events = len(unique_event_times)

        flags = np.zeros((num_of_unique_events, 24))

        for channel_event in channel_events:
            for i in range(num_of_unique_events):
                coincident_event_index = np.where(channel_event[0] == unique_event_times[i])[0]
                if len(coincident_event_index) > 0:
                    ind = coincident_event_index[0]
                    flags[i][channel_event[2]] = channel_event[1][coincident_event_index]
                else:
                    flags[i][channel_event[2]] = flags[i - 1][channel_event[2]]

        # Define the wait times between each command, aka the 'lengths' parameter.
        # Default unit for lengths is ns: multiply each length by 1e09
        lengths = []
        for i in range(num_of_unique_events - 1):
            lengths.append(round(np.asscalar((unique_event_times[i + 1] - unique_event_times[i]) * (1.e09)), 1))
        # if first instruction is a pulse, add some wait time to the end equal to the last pulse separation
        if unique_event_times[0] == 0:
            lengths.append(lengths[-2])
        #
        # flags is currently backwards, i.e. flags[0][0] represents the on-off state of the first pulse event of channel 0,
        # but commands have to be entered in the reverse order, i.e. flag[0][-1] should represent the on-off state of the first pulse
        # event of channel 0. binary_flag_list will be created to reflect this.
        binary_flag_list = []
        int_flag_list = []
        hex_flag_list = []
        for i in range(num_of_unique_events):
            flag_string = '0b'
            for j in range(self._CHANNELS - 1, -1, -1):
                flag_string += str(int(flags[i][j]))
            int_flag_list.append(int(flag_string, 2))
            binary_flag_list.append(flag_string)
            hex_flag_list.append(hex(int(flag_string, 2)))

        # if pulses do not start at t = 0s, wait until the first pulse begins
        # insert an initial command that turns all the channels off until the first pulse event occurs
        if self.getFirstSequenceEvent() != 0.0:
            lengths.insert(0, round(float(self.getFirstSequenceEvent()) * 1e09, 1))
            hex_flag_list.insert(0, '0x' + '{0:06x}'.format(0).upper())
            int_flag_list.insert(0, 0)
            binary_flag_list.insert(0, '0b' + '{0:024b}'.format(0))
            # last flag turns off all the channels, does not have to be included in commands. Last command will loop to first one
            binary_flag_list.pop(-1)
            int_flag_list.pop(-1)
            hex_flag_list.pop(-1)

        # Comment this to remove wait events
        for wait_event in self.wait_events:
            if wait_event > unique_event_times[-1]:
                int_flag_list.append(0)
                int_flag_list.append(0)
                lengths.append(round(float(wait_event - unique_event_times[-1]) * 1e09, 10))
                lengths.append(-1.0)
            else:
                insert_index = np.where(unique_event_times > wait_event)[0][0]
                lengths[insert_index] = float(lengths[insert_index] - (unique_event_times[insert_index] - wait_event))
                lengths.insert(insert_index + 1, float(unique_event_times[insert_index] - wait_event) * 1e09)
                lengths.insert(insert_index + 1, -1.0)
                int_flag_list.insert(insert_index + 1, int_flag_list[insert_index])
                int_flag_list.insert(insert_index + 1, 0)

        sec2ns = 1e09
        cycles_to_ns = (1 / 400.0) * 1e3  # since clockrate is given in MHz
        min_instruction_length = 5 * cycles_to_ns
        LONG_DELAY_TIMESTEP = 500e-09
        seq = []
        instructions = []
        flags_instr = int_flag_list
        lengths_instr = lengths
        num_of_instructions = len(int_flag_list)
        run_time = sum(lengths) / sec2ns
        found_bad_instruction = False

        # Possible chance that instruction set is a loop, but first instruction should be a long delay.
        # Solution: split the first instruction into two instructions, A and B. A has the same flags as the
        # the first instruction and it begins the loop. B also has the same flags, but 5*cycles_to_ns is
        # subtracted from its length. Do the same thing for the last instruction
        first_flag_instr = flags_instr[0]
        first_length_instr = lengths_instr[0]
        last_flag_instr = flags_instr[-1]
        last_length_instr = lengths_instr[-1]

        # If first instruction is to keep all the channels low:
        if first_flag_instr == 0:
            # Last instruction must be popped from lists because it is unique, it is used to signify the branch or the end of the loop
            # If last instruction length is long enough, subtract min_instruction_length from it
            #  since the final instruction  (branch or end_loop) will have length = min_instruction_length. This instruction does not need to be removed
            if last_length_instr > 2 * min_instruction_length:
                lengths_instr[-1] -= min_instruction_length
                last_length_instr = min_instruction_length
                last_flag_instr += self._ON
            # if short pulse, create the proper flags for this instruction:
            elif last_length_instr < min_instruction_length:
                if last_length_instr == 0:
                    last_flags_instr = flags_instr.pop(-1)
                    last_lengths_instr = lengths_instr.pop(-1)
                    lengths_instr.append(0)
                    flags_instr.append(0)
                else:
                    flags_instr.pop(-1)
                    lengths_instr.pop(-1)
                    num_of_instructions -= 1

                short_pulse_len = last_length_instr
                if (short_pulse_len < 1.5 * cycles_to_ns):
                    bnc_pulse_bits = self._ONE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 2.5 * cycles_to_ns):
                    bnc_pulse_bits = self._TWO_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 3.5 * cycles_to_ns):
                    bnc_pulse_bits = self._THREE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 4.5 * cycles_to_ns):
                    bnc_pulse_bits = self._FOUR_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 5 * cycles_to_ns):
                    bnc_pulse_bits = self._FIVE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 5.5 * cycles_to_ns):
                    bnc_pulse_bits = self._FIVE_PERIOD
                    inst_len = min_instruction_length + 1 * cycles_to_ns
                elif (short_pulse_len < 6 * cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 1 * cycles_to_ns
                elif (short_pulse_len < 7 * cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 2 * cycles_to_ns
                elif (short_pulse_len < 8 * cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 3 * cycles_to_ns
                last_length_instr = inst_len
                last_flag_instr += bnc_pulse_bits

            # else, instruction must be removed:
            else:
                flags_instr.pop(-1)
                lengths_instr.pop(-1)
                num_of_instructions -= 1
                last_flag_instr += self._ON

        if not inf_loop:
            # if first instruction is a regular instruction, pop it and use it as the LOOP command
            if first_length_instr < LONG_DELAY_TIMESTEP * sec2ns + min_instruction_length:
                seq.append('%s, LOOP, %s, %f ns' % ('{0:024b}'.format(first_flag_instr + self._ON), num_of_loops, first_length_instr))
                instructions.append((first_flag_instr, self._LOOP, num_of_loops, first_length_instr))
                flags_instr.pop(0)
                lengths_instr.pop(0)
                num_of_instructions -= 1
            # else, if first instruction is a long delay:
            else:
                # add a dummy instruction with length min_instruction_length to begin loop, then subtract min_instruction_length from original long_delay length
                lengths_instr[0] -= min_instruction_length
                seq.append('%s, LOOP, %s, %f ns' % ('{0:024b}'.format(0 + self._ON), num_of_loops, min_instruction_length))
                instructions.append((0, self._LOOP, num_of_loops, min_instruction_length))

        instructions_range = range(num_of_instructions)
        for inst in instructions_range:
            flag_instr = flags_instr[inst]
            length_instr = lengths_instr[inst]

            # wait event
            if length_instr == -1.0:
                seq.append('0, WAIT, 0, 0 ns')
                instructions.append((flag_instr, self._WAIT, 0, length_instr))

            elif length_instr > (2 ** 8) * cycles_to_ns:

                # LONG_DELAY
                # Disable short-pulse feature
                flag_instr += self._ON
                # number of cycles per LONG_DELAY_TIMESTEP
                cycles_per_LD = round(LONG_DELAY_TIMESTEP * sec2ns / cycles_to_ns)
                # how many long delays to make up length_instr? find that quotient
                long_delay_int = int((length_instr / sec2ns) // LONG_DELAY_TIMESTEP)
                # how much time remaining after that?
                remaining_time = round(length_instr - long_delay_int * LONG_DELAY_TIMESTEP * sec2ns, 1)

                if (abs(remaining_time - LONG_DELAY_TIMESTEP * sec2ns) < cycles_to_ns):
                    # making sure number of continue cycles is a good value
                    # if remaining_time is equal to LONG_DELAY_TIMESTEP to within one cycle, add one long delay instruction
                    # else, if remaining_time is equal to zero to within one cyce, set remaining_time equal to zero.
                    # These situations most likely occur because of rounding errors
                    long_delay_int += 1
                    remaining_time -= round(LONG_DELAY_TIMESTEP * sec2ns, 1)
                elif (abs(remaining_time - 0) < cycles_to_ns):
                    remaining_time = 0.0
                if long_delay_int > 1:
                    seq.append('%s, LONG_DELAY, %s, %f ns' % ('{0:024b}'.format(flag_instr), str(long_delay_int), LONG_DELAY_TIMESTEP * sec2ns))
                    instructions.append((flag_instr, self._LONG_DELAY, long_delay_int, LONG_DELAY_TIMESTEP * sec2ns))
                else:
                    seq.append('%s, CONTINUE, %s, %f ns' % ('{0:024b}'.format(flag_instr), str(0), LONG_DELAY_TIMESTEP * sec2ns))
                    instructions.append((flag_instr, self._CONTINUE, 0, LONG_DELAY_TIMESTEP * sec2ns))
                if remaining_time > 0:
                    seq.append('%s, CONTINUE, %s, %f ns' % ('{0:024b}'.format(flag_instr), str(0), remaining_time))
                    instructions.append((flag_instr, self._CONTINUE, 0, remaining_time))

            elif (length_instr >= min_instruction_length and length_instr <= (2 ** 8) * cycles_to_ns):
                # this is a regular instruction
                # Disable short-pulse feature
                flag_instr += self._ON
                long_delay_int = 0
                continue_cycles = length_instr
                seq.append('%s, CONTINUE, %s, %f ns' % ('{0:024b}'.format(flag_instr), str(0), length_instr))
                instructions.append((flag_instr, self._CONTINUE, 0, length_instr))
            elif length_instr < cycles_to_ns:
                # this is a bad instruction
                seq.append('----ignoring zero delay----')

            # if short pulse:
            elif 0 < length_instr < min_instruction_length:
                # this could be short pulse instruction
                short_pulse_len = length_instr
                seq.append('#### short pulses ####')
                # now have to use the same algorithm as in my C code
                #  if the delay value supplied to pb_inst_pbonly() is INST_LEN
                #   then the delay count written to the PB VLIW is 2
                #  hence changing the bits 21-23 will change the length of
                # pulses on BNC0-3
                # Since the pb_inst_pbonly function works by taking the length field and doing (length*clock_freq)-4
                #   to write onto the delay count, we invert that to get the delay
                #  count value we need.
                if flag_instr == 0:
                    bnc_pulse_bits = 0
                elif (short_pulse_len < 1.5 * cycles_to_ns):
                    bnc_pulse_bits = self._ONE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 2.5 * cycles_to_ns):
                    bnc_pulse_bits = self._TWO_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 3.5 * cycles_to_ns):
                    bnc_pulse_bits = self._THREE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 4.5 * cycles_to_ns):
                    bnc_pulse_bits = self._FOUR_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 5 * cycles_to_ns):
                    bnc_pulse_bits = self._FIVE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 5.5 * cycles_to_ns):
                    bnc_pulse_bits = self._FIVE_PERIOD
                    inst_len = min_instruction_length + 1 * cycles_to_ns
                elif (short_pulse_len < 6 * cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 1 * cycles_to_ns
                elif (short_pulse_len < 7 * cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 2 * cycles_to_ns
                elif (short_pulse_len < 8 * cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 3 * cycles_to_ns
                if inst < num_of_instructions - 1:
                    # if next low time is shorter than LONG_DELAY, incorporate this low time into the short-pulse instruction and then remove next low time
                    if lengths_instr[inst + 1] < LONG_DELAY_TIMESTEP * sec2ns - short_pulse_len:
                        inst_len = round(lengths_instr[inst + 1] + short_pulse_len, 1)
                        lengths_instr.pop(inst + 1)
                        flags_instr.pop(inst + 1)
                        num_of_instructions -= 1
                        instructions_range.pop(-1)
                    # else, next low time is a LONG_DELAY. In this case, subtract the mandatory low time of the short-pulse instruction from the next low time
                    else:
                        lengths_instr[inst + 1] -= round((min_instruction_length - short_pulse_len), 1)

                seq.append('%s, CONTINUE, %s, %f ns' % ('{0:024b}'.format(flag_instr + bnc_pulse_bits), str(0), inst_len))
                instructions.append((flag_instr + bnc_pulse_bits, self._CONTINUE, 0, inst_len))

        # end of the instruction loop

        if inf_loop:
            seq.append('%s, BRANCH, 0, %f ns' % ('{0:024b}'.format(last_flag_instr), last_length_instr))
            instructions.append((last_flag_instr, self._BRANCH, 'start', last_length_instr))
        else:
            seq.append('%s, END_LOOP, 0, %f ns' % ('{0:024b}'.format(last_flag_instr), last_length_instr))
            instructions.append((last_flag_instr, self._END_LOOP, 'start', last_length_instr))

        # Check for bad instructions (instructions s.t. length < 5 clock cycles of PB board). The exception is a WAIT command, which has a unique length = 0
        for inst in instructions:
            if inst[3] < min_instruction_length and inst[1] != self._WAIT:
                print('Bad instruction found!')
                print('Instruction length: ', inst[3])
                found_bad_instruction = True
                break

        return instructions, seq, run_time, found_bad_instruction

