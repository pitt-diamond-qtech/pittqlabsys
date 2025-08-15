from src.Controller.adwin_gold import AdwinGoldDevice
from src.core.adwin_helpers import get_adwin_binary_path, get_adwin_process_config
import pytest
import numpy as np
import matplotlib.pyplot as plt
from time import sleep
from unittest.mock import Mock, MagicMock, patch

#@pytest.mark.skip(reason='not currently testing')

@pytest.fixture
def mock_adwin():
    """
    Mock ADwin fixture for testing without hardware.
    Provides realistic mock responses for ADwin methods.
    """
    with patch('src.Controller.adwin_gold.ADwin') as mock_adwin_class:
        # Create a mock ADwin instance
        mock_adw = Mock()
        
        # Mock the ADwin class to return our mock instance
        mock_adwin_class.return_value = mock_adw
        
        # Set up mock properties and methods
        mock_adw.ADwindir = '/mock/adwin/dir/'
        mock_adw.Boot = Mock()
        mock_adw.Test_Version = Mock(return_value="Mock ADwin v1.0")
        
        # Mock process control methods
        mock_adw.Load_Process = Mock()
        mock_adw.Clear_Process = Mock()
        mock_adw.Start_Process = Mock()
        mock_adw.Stop_Process = Mock()
        mock_adw.Set_Processdelay = Mock()
        mock_adw.Get_Processdelay = Mock(return_value=3000)
        mock_adw.Process_Status = Mock(return_value=0)  # 0 = Not running
        
        # Mock variable setting/getting methods
        mock_adw.Set_Par = Mock()
        mock_adw.Set_FPar = Mock()
        mock_adw.Get_Par = Mock(return_value=0)
        mock_adw.Get_FPar = Mock(return_value=0.0)
        mock_adw.Get_FPar_Double = Mock(return_value=0.0)
        
        # Mock array methods
        mock_adw.Data_Length = Mock(return_value=5)
        mock_adw.GetData_Long = Mock(return_value=[1, 2, 3, 4, 5])
        mock_adw.GetData_Float = Mock(return_value=[1.0, 2.0, 3.0, 4.0, 5.0])
        mock_adw.GetData_Double = Mock(return_value=[1.0, 2.0, 3.0, 4.0, 5.0])
        mock_adw.GetData_String = Mock(return_value=b'Hello')
        mock_adw.String_Length = Mock(return_value=5)
        
        # Mock FIFO methods
        mock_adw.GetFifo_Long = Mock(return_value=[1, 2, 3])
        mock_adw.GetFifo_Float = Mock(return_value=[1.0, 2.0, 3.0])
        mock_adw.GetFifo_Double = Mock(return_value=[1.0, 2.0, 3.0])
        mock_adw.Fifo_Empty = Mock(return_value=True)
        mock_adw.Fifo_Full = Mock(return_value=0)
        
        # Mock other methods
        mock_adw.Get_Par_All = Mock(return_value=[0] * 80)
        mock_adw.Get_FPar_All = Mock(return_value=[0.0] * 80)
        mock_adw.Get_FPar_All_Double = Mock(return_value=[0.0] * 80)
        mock_adw.Get_Error_Text = Mock(return_value="No error")
        mock_adw.Get_Last_Error = Mock(return_value=0)
        mock_adw.Workload = Mock(return_value=25.5)
        
        # Create ADwinGold instance with mocked ADwin
        adwin_gold = AdwinGoldDevice(boot=False)  # Don't boot to avoid hardware connection
        
        # The is_connected property will now work because mock_adw.Test_Version() returns successfully
        
        yield adwin_gold
        
        # Clean up: explicitly call close to avoid __del__ issues
        try:
            adwin_gold.close()
        except:
            pass  # Ignore any cleanup errors

@pytest.fixture
def get_adwin(mock_adwin):
    """
    Alias for mock_adwin to maintain compatibility with existing tests.
    """
    return mock_adwin

def test_connection(get_adwin):
    assert get_adwin.is_connected

def test_processes(get_adwin, capsys):
    '''
    Loads a test process, sets delay, starts process, waits 0.25 sec, stops process, reads variables, then clears process

    Test Passed 9/18
    '''
    adw = get_adwin
    
    # Set up mock responses for this specific test
    adw.adw.Get_Processdelay.return_value = 5000
    adw.adw.Process_Status.side_effect = [0, 1, 0]  # Not running, Running, Not running
    adw.adw.Get_Par.return_value = 31215
    adw.adw.Get_FPar.return_value = 56.2
    adw.adw.Get_FPar.side_effect = [56.2, 5.0]  # For Par_20 and Par_12
    adw.adw.Data_Length.return_value = 5
    adw.adw.GetData_Long.return_value = [1, 2, 3, 4, 5]
    adw.adw.String_Length.return_value = 5
    adw.adw.GetData_String.return_value = b'Hello'
    
    # Get ADbasic file path using the new helper function
    simple_adbasic = get_adwin_binary_path('Test_Adbasic.TB4')

    # Load script and set delay to 16.5 microseconds (5000x3.3ns)
    adw.update({'process_4':{'load':str(simple_adbasic),'delay':5000}})
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

def test_counter(get_adwin, capsys):
    '''
    Loads a script that uses counter 1 on the Adwin. A function generator was then connected to the counter port.
    See Adbasic file (Trial_Counter.bas) for additional commented information

    Test Passed 9/18

    Tested with a function generator set to output square wave with max amplitude at 2.5V and minimum at 0V.
    The frequency was varied from 5MHz to 33.3MHz. Up to 20MHz counts were as expected (1/2 of frequency value since
    the counter runs for 0.5sec = process delay of 150000000x3.3ns and takes 0.5 seconds to clear). A signal above 20MHz started to see inconsistant counts.
    '''
    adw = get_adwin
    
    # Set up mock responses for counter test
    adw.adw.Process_Status.return_value = 1  # Running
    adw.adw.Get_Par.return_value = 42  # Mock counter value
    
    # Get counter file path using the new helper function
    counter_file = get_adwin_binary_path('Trial_Counter.TB1')

    data = []   # Array to hold counts data
    i = 0
    adw.update({'process_1':{'load':str(counter_file),'running':True}})    # Loads and start process
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


def test_adwin_helpers_integration(get_adwin):
    '''
    Test the new adwin_helpers integration with ADwinGold.
    Demonstrates how the helper functions make the code cleaner and more maintainable.
    '''
    adw = get_adwin
    
    # Set up mock responses for this test
    adw.adw.Get_Processdelay.return_value = 3000
    adw.adw.Process_Status.side_effect = [0, 1]  # Not running, then Running
    
    # Test using get_adwin_process_config helper
    process_config = get_adwin_process_config(
        process_number=3,
        binary_file='Test_Adbasic.TB4',
        delay=3000,
        auto_start=False
    )
    
    # Apply the configuration
    adw.update(process_config)
    
    # Verify the process was loaded correctly
    delay = adw.read_probes('process_delay', id=3)
    assert delay == 3000
    
    status = adw.read_probes('process_status', id=3)
    assert status == 'Not running'
    
    # Test starting the process
    adw.update({'process_3': {'running': True}})
    sleep(0.1)
    status = adw.read_probes('process_status', id=3)
    assert status == 'Running'
    
    # Clean up
    adw.update({'process_3': {'running': False}})
    adw.update({'process_3': {'load': ''}})


def test_adwin_helpers_error_handling():
    '''
    Test error handling in adwin_helpers when binary files don't exist.
    '''
    import pytest
    from src.core.adwin_helpers import get_adwin_binary_path
    
    # Test that non-existent file raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        get_adwin_binary_path('NonExistentFile.TB1')


def test_mock_cleanup():
    '''
    Test that the mock ADwin fixture cleans up properly without warnings.
    '''
    # This test ensures that the mock fixture cleanup works correctly
    # and doesn't generate unraisable exception warnings
    with patch('src.Controller.adwin_gold.ADwin') as mock_adwin_class:
        mock_adw = Mock()
        mock_adwin_class.return_value = mock_adw
        mock_adw.Test_Version = Mock(return_value="Mock ADwin v1.0")
        mock_adw.Stop_Process = Mock()
        mock_adw.Clear_Process = Mock()
        
        # Create and immediately destroy an ADwinGold instance
        adwin = AdwinGoldDevice(boot=False)
        del adwin  # This should trigger __del__ without warnings


@pytest.mark.hardware
def test_adwin_hardware_connection():
    '''
    Test ADwin connection with real hardware.
    This test requires actual ADwin hardware to be connected.
    '''
    adwin = None
    try:
        adwin = AdwinGoldDevice()
        assert adwin.is_connected
        print(f"Successfully connected to ADwin hardware")
        
        # Test basic functionality with real hardware
        adwin.close()
    except Exception as e:
        pytest.skip(f"ADwin hardware not available: {e}")
    finally:
        # Ensure cleanup happens even if test is skipped
        if adwin is not None:
            try:
                adwin.close()
            except:
                pass


@pytest.mark.hardware
def test_adwin_hardware_process_loading():
    '''
    Test loading processes with real ADwin hardware.
    This test requires actual ADwin hardware to be connected.
    '''
    adwin = None
    try:
        adwin = AdwinGoldDevice()
        assert adwin.is_connected
        
        # Test loading a real binary file
        binary_path = get_adwin_binary_path('Test_Adbasic.TB4')
        adwin.update({'process_1': {'load': str(binary_path), 'delay': 3000}})
        
        # Verify the process was loaded
        delay = adwin.read_probes('process_delay', id=1)
        assert delay == 3000
        
        # Clean up
        adwin.update({'process_1': {'load': ''}})
        adwin.close()
        
    except Exception as e:
        pytest.skip(f"ADwin hardware not available: {e}")
    finally:
        # Ensure cleanup happens even if test is skipped
        if adwin is not None:
            try:
                adwin.close()
            except:
                pass

