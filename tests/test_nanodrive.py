from src.Controller.nanodrive import MCLNanoDrive
import pytest
import numpy as np
import matplotlib.pyplot as plt
from time import sleep

#@pytest.mark.skip(reason='not currently testing')

@pytest.fixture
def get_nanodrive() -> MCLNanoDrive:
    return MCLNanoDrive()

def test_connection(get_nanodrive):
    assert get_nanodrive.is_connected

def test_position(get_nanodrive):
    '''
    Read axis range and ensures it is a float. Sets axis position and read to make sure it is within 10 nm of specified

    Test passed 7/22/24
    '''
    nd = get_nanodrive
    ax_range = nd.read_probes('axis_range')
    nd.update(settings={'x_pos':5})
    sleep(0.1)
    pos = nd.read_probes('x_pos')
    assert isinstance(ax_range, float)
    assert 4.99 <= pos <= 5.01 #check to make sure atleast within 10 nm. Usally closer than 10nm to inputed position but not exact


@pytest.mark.parametrize('clock',['Pixel','Line','Frame','Aux'])
@pytest.mark.parametrize('mode',[0,1])
def test_clock_mode(get_nanodrive,clock,mode):
    '''
    Code Testing: Iterates through mode settings of each clock to make sure there is no error from error dictionary.
        Passes if no 'raise' triggered in code
    Physically tested using an oscilliscope and outputs on back of NanoDrive
        Pass if clock is set to proper mode after command

    Tested using scope and clock_functions method 7/22/24 - Dylan
    Added to update method and tested using scope 8/26/24
    pytest passed 7/22/24
    '''
    get_nanodrive.clock_functions(clock, mode=mode)
    sleep(0.1)


@pytest.mark.parametrize('polarity',[0,1])
@pytest.mark.parametrize('clock',['Pixel','Line','Frame','Aux'])
def test_clock_polarity(get_nanodrive,clock,polarity):
    '''
    Code Testing: Iterates through polarity settings of each clock to make sure there is no error from error dictionary.
        Passes if no 'raise' triggered in code
    Physically tested using an oscilliscope and outputs on back of NanoDrive
        -Mode of each clock is set to low and the polarity is set as low-to-high. Passes if triggering a pulse puts clock to high
        -Also works vice versa (mode: high, polarity: high-to-low)
        -Also a test to confirm pulse command triggers

    Tested using scope and clock_functions method 7/22/24 - Dylan
    Added to update method and tested using scope 8/26/24
    Test passed 7/23/24
        -When run 8 times (4x2 parameters) fails but if ran with 2 clocks than again with other 2 clocks works fine
    '''
    get_nanodrive.clock_functions(clock, polarity=polarity)
    sleep(0.1)

@pytest.mark.parametrize('polarity',[0,1,2])
@pytest.mark.parametrize('binding',['x','y','z','read','load'])
@pytest.mark.parametrize('clock',['Pixel','Line','Frame','Aux'])
def test_clock_binding(get_nanodrive,clock,binding,polarity):
    '''
    Code Testing: Iterates through binding option to make sure commands dont trigger error dictionary
        Passes if no 'raise' triggered in code
    Physically tested using oscilliscope in the same mannor as test_clock_polarity

    Tested using scope 7/22/24 - Dylan
    Test passed 7/23/24
        -60 commands send with current parametrize setup 5 fail (says invalid handle error). These failures seem to be
         an artifact of pytest. The failures always occur at the same test number (14,21,35,42,56) regardless of what command is sent.
        -All combinations of which clock, the binding and polarity have passed in separate tests
    '''
    nd = get_nanodrive
    nd.clock_functions(clock,polarity=polarity, binding=binding)
    sleep(0.1)

def test_clock_reset(get_nanodrive):
    '''
    Test to see if error when sending reset command. Note pixel input is arbitrary ALL clocks are reset to defaults

    Test passed 7/22/24
    '''
    get_nanodrive.clock_functions('Pixel',reset=True)

def test_single_ax_waveform(capsys,get_nanodrive):
    '''
    1) Loads waveform and then reads waveform on x-axis
    2) Sets up load and sets up read then triggers waveform acquisition on y-axis

    Plot of x_read and y_read are shifted slightly from inputted but overall fairly consistent.
        -waveform_acquisition get more consistant read values however cant control read delay before load starts
    Seems like read start a few ms before position changes
        -approx 4 data points are read at 0 before position is updated (4x2ms=8ms delay maybe)

    Test passed 7/22/24
    '''
    wf = list(np.arange(0,10.1,0.1)) #wavefrom must be a list for internal conversion/checks
    nd = get_nanodrive
    nd.update(settings={'x_pos': 0, 'y_pos': 0})

    sleep(0.5)
    nd.update(settings={'axis':'x','num_datapoints':len(wf),'load_waveform':wf})
    sleep(1/1000)
    #no sleep here makes read_probes have same reading as waveform_acquistion
    #sleep of a very small time gives a slightly more accurate reading of shifted up from inputed by ~0.1
    x_read = nd.read_probes('read_waveform',axis='x')
    sleep(1)    #sleep may not be neccesary but I dont want/need to trigger both axes at once

    nd.setup(settings={'axis':'y','num_datapoints':len(wf),'load_waveform':wf,'read_waveform':nd.empty_waveform})
    y_read = nd.waveform_acquisition(axis='y')
    #sleeps added so NanoDrive finishs processing one command before another is sent

    with capsys.disabled():
        plt.figure(figsize=(10, 6))
        plt.plot(wf, x_read, label='Load than read waveform', marker='o')
        plt.plot(wf, y_read, label='Set load and read then acquisition', marker='x')
        plt.plot(wf, wf, label='Input waveform', linestyle='--')

        plt.xlabel('Input Waveform')
        plt.ylabel('Read Values')
        plt.title('Comparison of read vs inputed waveform')
        plt.legend()
        plt.grid(True)
        plt.show()
    assert len(wf) == len(x_read) == len(y_read)
    #also tested with reverse: wf_reveresed = np.arange(0, 10.1, 0.1)[::-1]


def test_mult_ax_waveform(capsys,get_nanodrive):
    '''
    Sets up, triggers, then read a multi axis waveform. Plots read data to compare with inputed

    Succesfully runs waveform; device moves; no errors. Reading mult_ax_waveform has position data as 0!
    Same read results as old code. Read multi axis waveform isn't typically used so fine that read values are wrong
    '''
    mult_wf = [list(np.arange(0,10.1,0.1)),list(np.arange(0,10.1,0.1)),[0]]
    nd = get_nanodrive
    nd.update(settings={'x_pos': 0, 'y_pos': 0, 'z_pos': 0})

    nd.setup(settings={'num_datapoints':len(mult_wf[0]),'mult_ax':{'waveform':mult_wf,'time_step':1,'iterations':1}})
    nd.trigger('mult_ax')
    read_wf = nd.read_probes('mult_ax_waveform')

    with capsys.disabled():
        fig, axs = plt.subplots(1, 3, figsize=(18, 6))

        axs[0].plot(mult_wf[0], label='Loaded waveform')
        axs[0].plot(read_wf[0], label='Read wavefrom', linestyle='--')
        axs[0].set_title('x-axis')

        axs[1].plot(mult_wf[1], label='Loaded waveform')
        axs[1].plot(read_wf[1], label='Read waveform', linestyle='--')
        axs[1].set_title('y-axis')

        axs[2].plot(mult_wf[2], label='Loaded waveform')
        axs[2].plot(read_wf[2], label='Read waveform', linestyle='--')
        axs[2].set_title('z-axis')

        for i in range(3):
            axs[i].set_xlabel('Index')
            axs[i].set_ylabel('Waveform value')
            axs[i].legend()
            axs[i].grid(True)

        plt.suptitle('Loaded and Read Waveforms for Multi-Axis Command')
        plt.show()

    assert len(read_wf[0]) == len(read_wf[1]) == len(read_wf[2])


def test_continuos_mult_ax_waveform(get_nanodrive):
    '''
    Triggers and infinite mult_ax waveform, waits 1 second then stops

    Test passed 7/22/24
    '''
    mult_wf = [list(np.arange(0, 10.1, 0.1)), list(np.arange(0, 10.1, 0.1)), [0]]
    nd = get_nanodrive
    nd.update(settings={'x_pos': 0, 'y_pos': 0, 'z_pos': 0})

    #iterations = 0 is for infinite loop
    nd.setup(settings={'num_datapoints':len(mult_wf[0]),'mult_ax': {'waveform': mult_wf, 'time_step': 1, 'iterations': 0}})
    nd.trigger('mult_ax')
    sleep(1)
    nd.trigger('mult_ax',mult_ax_stop=True)





