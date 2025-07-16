from src.Controller.nanodrive import MCLNanoDrive
import pytest
import numpy as np
import matplotlib.pyplot as plt
from time import sleep

#@pytest.mark.skip(reason='not currently testing')

@pytest.fixture
def get_nanodrive() -> MCLNanoDrive:
    return MCLNanoDrive(settings={'serial':2849})

def test_connection(get_nanodrive):
    assert get_nanodrive.is_connected

@pytest.mark.skip(reason='not currently testing')
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

@pytest.mark.skip(reason='not currently testing')
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

@pytest.mark.skip(reason='not currently testing')
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

@pytest.mark.skip(reason='not currently testing')
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

@pytest.mark.skip(reason='not currently testing')
def test_clock_reset(get_nanodrive):
    '''
    Test to see if error when sending reset command. Note pixel input is arbitrary ALL clocks are reset to defaults

    Test passed 7/22/24
    '''
    get_nanodrive.clock_functions('Pixel',reset=True)

@pytest.mark.skip(reason='not currently testing')
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

@pytest.mark.skip(reason='not currently testing')
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

@pytest.mark.skip(reason='not currently testing')
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

@pytest.mark.skip(reason='not currently testing')
@pytest.mark.parametrize('read_rate',[0.5,1,2])
@pytest.mark.parametrize('load_rate',[1,2,5])
@pytest.mark.parametrize('step',[1.0,0.1])
@pytest.mark.parametrize('y_min',[50.0,70.0,85.0])
def test_waveform_for_confocal_scan(capsys,get_nanodrive,read_rate,load_rate,step,y_min):
    '''
    Issue:
        When running the ConfocalScan_OldMethod (fast scan) we saw a shift in the image compared to the slow, consistant point by point scan.
    Solution:
        The shift caused by using the MCL Nanodrive waveform is related to the number of datapoints in the waveform. When loading a waveform
        there is always a 'warm-up' and 'cool-down' time were the device moves quadratically not linearly. To conpensate for this lack we start
        waveforms 5 um before the desired start and end 5 um after. The data arrays are then manipulated to get the correct data.

        Below is the logic of this process. The pytest parametrizations are used to ensure the logic works regaurdless of the wavefunction parameters.
        This method seems to work really well as long as the waveform is long enough (> 40 points approximatly). See excel file for more information
        D:\Data\dylan_staples\ADwin Counter and Nanodrive Waveform tests.xlsx

    Also tested with step size of 0.01 which worked the best because it has the most points in a waveform. It  is not added to the parametrization
    as it takes a long time to run and can lead to error if the waveform is longer than the allowed 6666 points (nanodrive hardware limitation)

    Test Passed 4/29/2025 - Dylan Staples
    See confocal.py experiment to see implementation
    '''
    read_rate = read_rate
    load_rate = load_rate
    LR = load_rate/read_rate

    y_min = y_min
    y_max = 95.0
    step = step
    y_array = np.arange(y_min,y_max+step,step)

    y_before = np.arange(y_min-5.0,y_min,step)
    y_after = np.arange(y_max+step, y_max+5.0+step, step)
    #adjusted array with elements 5 um before and after desired waveform to compensate for start up and cool down periods. The same step size seems to give best results
    y_array_adj = np.insert(y_array,0,y_before)
    y_array_adj = np.append(y_array_adj,y_after)

    #extend y_array for plotting reason
    last_val = y_array_adj[-1]
    extension = np.array([last_val + step * (i + 1) for i in range(20)])
    y_array_adj_extended = np.concatenate((y_array_adj,extension))

    wf = list(y_array_adj)
    len_wf = len(y_array_adj)

    nd = get_nanodrive
    nd.update(settings={'x_pos': 0, 'y_pos': y_min-5,'read_rate':read_rate,'num_datapoints':len_wf,'load_rate':load_rate})
    sleep(0.1)

    nd.setup(settings={'num_datapoints':len(wf),'load_waveform':wf},axis='y')
    read_length = int(LR*len(wf)+50)
    nd.setup(settings={'num_datapoints': read_length, 'read_waveform': nd.empty_waveform},axis='y')  # read an extra 20 points
    y_read = nd.waveform_acquisition(axis='y')

    max_sleep = max(load_rate,read_rate)
    sleep(len_wf*max_sleep/1000)
    #sleeps added so NanoDrive finish waveform

    #read and load time are the time stamps for points on a waveform being loaded and for points of the waveform being read
    #two different lines for array length differences and read/load rate difference
    read_time = np.arange(len(y_read))*read_rate
    load_time = np.arange(len(wf))*load_rate
    load_time_extended = np.arange(len(y_array_adj_extended))*load_rate

    y_read_array = np.array(y_read)
    #index for the point of the read array when at y_min and y_max
    lower_index = np.where((y_read_array > y_min-step/LR) & (y_read_array < y_min+step/LR))[0]
    upper_index = np.where((y_read_array > y_max-step/LR) & (y_read_array < y_max+step/LR))[0]

    #in experiment these would be index of count_data for points from y_min to y_max
    load_lower_index = int(lower_index[0]/LR)
    load_upper_index = int(upper_index[0]/LR)

    with capsys.disabled():
        plt.figure(figsize=(10, 6))

        plt.plot(read_time, y_read, label='Read waveform', marker='.', linestyle='none')
        plt.plot(load_time_extended,y_array_adj_extended,alpha=0.1,marker='.',color='m',label='Extended Waveform')
        plt.plot(load_time, wf, label='Input waveform', marker='.',color='orange')

        #region of interest
        plt.axhline(y=y_max, color='r', linestyle='--', linewidth=1.5,label='ROI')
        plt.axhline(y=y_min, color='r', linestyle='--', linewidth=1.5,)
        plt.axvline(x=read_time[lower_index[0]], color='r', linestyle='--', linewidth=1.5)
        plt.axvline(x=read_time[upper_index[0]], color='r', linestyle='--', linewidth=1.5)

        plt.plot([load_time[load_lower_index]],[y_array_adj_extended[load_lower_index]],color='g', label='Index of Count Data',marker='.')
        plt.plot([load_time_extended[load_upper_index]],[y_array_adj_extended[load_upper_index]],color='g',marker='.')

        plt.xlabel('Time (ms)')
        plt.ylabel('Y position (um)')
        plt.title(f'Parameters: Number of points = {len(wf)}, Load Rate = {load_rate}ms, Read Rate = {read_rate}ms')
        plt.legend()
        plt.grid(True)
        plt.show()


