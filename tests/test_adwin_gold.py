from src.Controller.adwin import ADwinGold
import pytest
import os
import numpy as np
import matplotlib.pyplot as plt
from time import sleep

#@pytest.mark.skip(reason='not currently testing')

@pytest.fixture
def get_adwin() -> ADwinGold:
    return ADwinGold()

def test_connection(get_adwin):
    assert get_adwin.is_connected

def test_processes(get_adwin,capsys):
    '''
    Loads a test process, sets delay, starts process, waits 0.25 sec, stops process, reads variables, then clears process

    Test Passed 9/18
    '''
    adw = get_adwin
    #get adbasic file path
    root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
    simple_adbasic = os.path.join(root_directory, 'src', 'Controller', 'binary_files', 'ADbasic', 'testing_scripts', 'Test_Adbasic.TB4')


    #load script and set delay to 16.5 microseconds (5000x3.3ns)
    adw.update({'process_4':{'load':simple_adbasic,'delay':5000}})
    delay = adw.read_probes('process_delay',id=4)
    assert delay == 5000

    status1 = adw.read_probes('process_status',id=4)    #reads process status for process 4
    assert status1 == 'Not running'

    adw.update({'process_4':{'running':True}})
    sleep(0.125)
    status2 = adw.read_probes('process_status',id=4)
    assert status2 == 'Running'

    #test setting Par and FPar
    adw.set_int_var(Par_id=20,value=31215)
    adw.set_float_var(FPar_id=20,value=56.2)
    Par_20 = adw.read_probes('int_var',id=20)
    FPar_20 = adw.read_probes('float_var',id=20)
    assert Par_20 == 31215 and (FPar_20 <= 56.201 or FPar_20 >= 56.199)

    adw.update({'process_4':{'running':False}})
    adw.stop_process(4)
    sleep(0.25) #gives time for process to stop
    status3 = adw.read_probes('process_status',id=4)
    assert status3 == 'Not running'

    #set FPar_12 = 5.0, Data_56 = [1,2,3,4,5], and Data_8 = 'Hello' in ADbasic script
    FPar_12 = adw.read_probes('float_var',id=12)
    length_data_56 = adw.read_probes('array_length',id=56)
    Data_56 = list(adw.read_probes('int_array',id=56,length=length_data_56))                #array read as a C object; use list() to make user friendly
    length_str = adw.read_probes('str_length',id=8)
    str_Data_8 = adw.read_probes('str_array',id=8,length=length_str).decode('utf-8')        #string in binary so decode to strip of b''
    assert FPar_12 == 5.0  and str_Data_8 == 'Hello' and Data_56 == [1,2,3,4,5]


    adw.update({'process_4':{'load':''}})   #clears process by entering load as an empty string

    with capsys.disabled():
        print('Statuses: ',status1,' ',status2,' ',status3,'\n',
              'Variables: ',FPar_12,' ',Data_56,' ',str_Data_8,'\n',Par_20,' ',FPar_20)

def test_counter(get_adwin,capsys):
    '''
    Loads a script that uses counter 1 on the Adwin. A function generator was then connected to the counter port.
    See Adbasic file (Trial_Counter.bas) for additional commented information

    Test Passed 9/18

    Tested with a function generator set to output square wave with max amplitude at 2.5V and minimum at 0V.
    The frequency was varied from 5MHz to 33.3MHz. Up to 20MHz counts were as expected (1/2 of frequency value since
    the counter runs for 0.5sec = process delay of 150000000x3.3ns and takes 0.5 seconds to clear). A signal above 20MHz started to see inconsistant counts.
    '''
    root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    counter_file = os.path.join(root_directory, 'src', 'Controller', 'binary_files','ADbasic', 'Trial_Counter.TB1')
    #counter_file = 'D:PycharmProjects/pittqlabsys/src/Controller/binary_files/ADbasis\Trial_Counter.TB1'

    adw = get_adwin
    data = []   #array to hold counts data
    i = 0
    adw.update({'process_1':{'load':counter_file,'running':True}})    #loads and start process
    cnt_status = adw.read_probes('process_status',id=1)
    assert cnt_status == 'Running'

    while i < 20:
        raw_value = adw.read_probes('int_var',id=1)
        data.append(raw_value)
        i += 1
        sleep(0.1)      #sleep for short time to make bins of 'size' 0.1 seconds

    adw.update({'process_1':{'running':False}})

    with capsys.disabled():
        print('File: ',counter_file)
        print('Counts :',data)

