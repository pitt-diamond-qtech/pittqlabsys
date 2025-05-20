from src.core import Device, Parameter
import ADwin
from ADwin import ADwinError
#from ctypes import *


class ADwinGold(Device):
    '''
    This class implements the ADwin Gold II by booting it with the T11 processor. It does not yet implement TiCO processes.
    Processes should be written in an ADbasic script and then loaded using this controller (note the inital processes delay set in each script).
    The processor and priority can be changed for each process and is left to the user writing the ADbasic script.
    '''

    _DEFAULT_SETTINGS = Parameter([
        Parameter('process_1',[
            Parameter('load','',str,'Filename to load (should end with .__1 for process 1). Input empty string to clear process'),
            Parameter('delay',3000,int,'Time interval between executions of the event section (time = delay x 3.3ns)'),
            Parameter('running',False,bool,'Start and stop process')
            ]),
        Parameter('process_2', [
            Parameter('load', '', str, 'Filename to load (should end with .__2 for process 2). Input empty string to clear process'),
            Parameter('delay',3000,int,'Time interval between executions of the event section (time = delay x 3.3ns)'),
            Parameter('running',False,bool,'Start and stop process')
            ]),
        Parameter('process_3', [
            Parameter('load', '', str, 'Filename to load (should end with .__3  for process 3). Input empty string to clear process'),
            Parameter('delay',3000,int,'Time interval between executions of the event section (time = delay x 3.3ns)'),
            Parameter('running',False,bool,'Start and stop process')
        ]),
        Parameter('process_4', [
            Parameter('load', '', str, 'Filename to load (should end with .__4 for process 4). Input empty string to clear process'),
            Parameter('delay',3000,int,'Time interval between executions of the event section (time = delay x 3.3ns)'),
            Parameter('running',False,bool,'Start and stop process')
        ]),
        Parameter('process_5', [
            Parameter('load', '', str, 'Filename to load (should end with .__5 for process 5). Input empty string to clear process'),
            Parameter('delay',3000,int,'Time interval between executions of the event section (time = delay x 3.3ns)'),
            Parameter('running',False,bool,'Start and stop process')
        ]),
        Parameter('process_6', [
            Parameter('load', '', str, 'Filename to load (should end with .__6 for process 6). Input empty string to clear process'),
            Parameter('delay',3000,int,'Time interval between executions of the event section (time = delay x 3.3ns)'),
            Parameter('running',False,bool,'Start and stop process')
        ]),
        Parameter('process_7', [
            Parameter('load', '', str, 'Filename to load (should end with .__7 for process 7). Input empty string to clear process'),
            Parameter('delay',3000,int,'Time interval between executions of the event section (time = delay x 3.3ns)'),
            Parameter('running',False,bool,'Start and stop process')
        ]),
        Parameter('process_8', [
            Parameter('load', '', str, 'Filename to load (should end with .__8 for process 8). Input empty string to clear process'),
            Parameter('delay',3000,int,'Time interval between executions of the event section (time = delay x 3.3ns)'),
            Parameter('running',False,bool,'Start and stop process')
        ]),
        Parameter('process_9', [
            Parameter('load', '', str, 'Filename to load (should end with .__9 for process 9). Input empty string to clear process'),
            Parameter('delay',3000,int,'Time interval between executions of the event section (time = delay x 3.3ns)'),
            Parameter('running',False,bool,'Start and stop process')
        ]),
        Parameter('process_10', [
            Parameter('load', '', str, 'Filename to load (should end with .__10 for process 10). Input empty string to clear process'),
            Parameter('delay',3000,int,'Time interval between executions of the event section (time = delay x 3.3ns)'),
            Parameter('running',False,bool,'Start and stop process')
        ]),
    ])

    def __init__(self, name=None, settings=None, boot=True, num_devices=1):
        super(ADwinGold, self).__init__(name, settings)

        self.adw = ADwin.ADwin(DeviceNo=num_devices, raiseExceptions=1)
        #boots the ADwin which resets processes and global variables. Input boot = False if ADwin is already initilized
        if boot:
            try:
                #boots with T11 processor. 3.333.. ns minimum time resolution for low and high priority processes
                btl = self.adw.ADwindir+'ADwin11.btl' #could add flexibiliy for which processor if device has multiple
                self.adw.Boot(btl)
            except ADwinError as e:
                print('Issue booting ADwin: ',e)
                raise

    def update(self, settings):
        """
        Updates and controls internal processes of the ADwin both in the code and in the hardware.
        Args:
            settings: a dictionary in the standard settings format
        """
        super(ADwinGold, self).update(settings)

        if self._settings_initialized:
            for key, value in settings.items():
                process_number = int(key.split('_')[-1]) #gets number after '_' in process_# key
                for param, param_value in value.items():
                    if param == 'load':
                        if param_value == '' or param_value == ' ':   #will clear the process if load is updated to be empty
                            self.clear_process(process_number)
                        else:
                            self.load_process(param_value)  #loads binary file ex. 'D:/PyCharmProjects/.../test_process.TB2'
                            #may want to add some way to make sure a process isnt loaded over another as it can cause memory fragmenting
                    elif param == 'delay':
                        self.adw.Set_Processdelay(process_number, param_value)
                    elif param == 'running':
                        if param_value == True:
                            self.start_process(process_number)
                        elif param_value == False:
                            self.stop_process(process_number)


    def load_process(self, filepath):
        '''
        Loads a binary file created using ADbasic (max 10).
        Note: Only variables defined in the ADbasic script can be interacted with in the python code else will return 0.
        Args:
            filepath: file location of ADbasic script
                -If the ADbasic files are in an 'ADbasic' subfolder in the same location as the controller can use
                    os.path.join(os.path.dirname(__file__),'ADbasic\\__name__.__(processor & number)__')
                -If using in GUI can copy path and paste.

        Note: There is some subtlties with python handling paths. The direction and number of slashes should follow
              the example path of test_script

        test_script located at 'D:/PyCharmProjects/pittqlabsys-main/src/Controller\ADbasic\\Test_controller.TB1'
        '''
        self.adw.Load_Process(filepath)

    def clear_process(self, number):
        '''
        Clears a process from ADwin memory. Will trigger if 'load' = '' (empty string) for each process_# parameter.
        Args:
            number: number corresponding to process defined in file path ex. test_process.TB2 is process 2
        '''
        self.adw.Clear_Process(number)


    def start_process(self, number):
        '''
        Starts a loaded process
        Note: Starting a process executes init section of process
        Args:
            number: number corresponding to process defined in file path ex. test_process.TB3 is process 3
        '''
        self.adw.Start_Process(number)

    def stop_process(self, number):
        '''
        Stops a running process. Can use read_probes('process_status', {process number}) to see if process is running, stoping, or not running
        Note: stoping a process executes finish section of process
        Args:
            number: number corresponding to process defined in file path ex. test_process.TB4 is process 4
        '''
        self.adw.Stop_Process(number)

    def close(self):
        '''
        Stops and clears all processes. If some are not running/not loaded commands do nothing.
        '''
        for i in range(1,11):
            self.stop_process(i)
            self.clear_process(i)

    def set_int_var(self, Par_id, value):
        '''
        Changes value of specified global parameter Par_#
        Args:
            Par_id: index of global integer variable (range Par_1 to Par_80)
            value: integer value to write to parameter (32-bit integer)
        '''
        value = int(value)
        if (Par_id < 1) or (Par_id > 80):
            raise KeyError
        self.adw.Set_Par(Par_id, value)

    def set_float_var(self, FPar_id, value):
        '''
        Changes value of specified global parameter FPar_#
        Args:
            FPar_id: index of global float variable (range FPar_1 to FPar_80)
            value: float value to write to parameter
        '''
        value = float(value)
        if (FPar_id < 1) or (FPar_id > 80):
            raise KeyError
        self.adw.Set_FPar(FPar_id, value)

    def reboot_adwin(self,num_devices=1):
        new_adw_handle = None
        try:
            # boots with T11 processor. 3.333.. ns minimum time resolution for low and high priority processes
            new_adw_handle = ADwin.ADwin(DeviceNo=num_devices, raiseExceptions=1)
            btl = new_adw_handle.ADwindir + 'ADwin11.btl'
            new_adw_handle.Boot(btl)
        except ADwinError as e:
            print('Issue rebooting ADwin: ', e)
            raise
        if new_adw_handle is not None:
            self.adw = new_adw_handle

    def __del__(self):  #should stop all processes when ADwin is closed or a crash occures
        self.close()

    def read_probes(self, key, id=1, length=100):
        '''
        Sends a command to/through ADbasic script that returns the value of a varible or some other device parameter.
        Args:
            key: see _PROBES for options and descriptions
            id: number of array, variable, or process
                -read_probes can only take 1 argument so necessary to set id=1 and have user enter id=# when needed in python script
            length: number of entries to read from array; will always start at the first index
                -can use read_probes('array_length') to get actual length althrough it is sometimes misleading
        '''
        assert(self._settings_initialized)
        assert key in list(self._PROBES.keys())
        value = None #parameters are different from probes. Setting value=none fixes error when trying to return value befor defining
        if key == 'array_length':   #only gets length of Data_# arrays
            value = self.adw.Data_Length(id)

        elif key == 'int_var':
            value = self.adw.Get_Par(id)
        elif key == 'float_var':
            value = self.adw.Get_FPar(id)
        elif key == 'float64_var':
            value = self.adw.Get_FPar_Double(id)

        elif key == 'all_ints':
            value = self.adw.Get_Par_All()
        elif key == 'all_floats':
            value = self.adw.Get_FPar_All()
        elif key == 'all_float64s':
            value = self.adw.Get_FPar_All_Double()

        elif key == 'int_array':
            value = self.adw.GetData_Long(id, 1 ,length)
        elif key == 'float_array':
            value = self.adw.GetData_Float(id, 1, length)
        elif key == 'float64_array':
            value = self.adw.GetData_Double(id, 1, length)
        elif key == 'str_array':
            value = self.adw.GetData_String(id, length)

        #can use read_probes('fifo_full') to get how many elements are in a Fifo array
        elif key == 'int_fifo':
            value = self.adw.GetFifo_Long(id, 1, length)
        elif key == 'float_fifo':
            value = self.adw.GetFifo_Float(id, 1, length)
        elif key == 'float_64_fifo':
            value = self.adw.GetFifo_Double(id, 1, length)
        elif key == 'fifo_empty':
            value = self.adw.Fifo_Empty(id)
        elif key == 'fifo_full':
            value = self.adw.Fifo_Full(id)

        elif key == 'str_length':
            value = self.adw.String_Length(id)
        elif key == 'process_delay':
            value = self.adw.Get_Processdelay(id)
        elif key == 'process_status':
            rawvalue = self.adw.Process_Status(id)
            value = self._internal_to_status(rawvalue)
        elif key == 'last_error':
            value = self.adw.Get_Error_Text(self.adw.Get_Last_Error())
        elif key == 'workload':
            value = self.adw.Workload()

        return value

    @property
    def _PROBES(self):
        return {
            #read variables of different types
            'int_var':'Returns Par_{id}', 'float_var':'Returns FPar_{id}', 'float64_var':'Returns 64bit FPar_{id}',
            'all_ints':'Returns all Par', 'all_floats':'Returns all FPar', 'all_float64s':'Returns all 64bit FPar',
            #data arrays
            'int_array':'Returns Data_{id} defined as Long',
            'float_array':'Returns Data_{id} defined as Float',
            'float64_array':'Returns Data_{id} defined as Float64',
            'str_array':'Returns Data_{id} defined as String',
            #fifo arrays
            'int_fifo':'Returns Data_{id} defined as Long as Fifo',
            'float_fifo': 'Returns Data_{id} defined as Float as Fifo',
            'float64_fifo':'Returns Data_{id} defined as Float64 as Fifo',
            'fifo_empty':'number of empty elements',
            'fifo_full':'number of used elements',
            #other
            'array_length':'length of defined array',
            'str_length':'length of string array',
            'process_delay':'checks delay between events of a process',
            'process_status':'checks status of a process',
            'last_error':'checks last error encountered',
            'workload':'returns workload of adwin as a percent of max'

        }

    @property
    def is_connected(self):
        try:
            self.adw.Test_Version()     #arbitrary query to test for a response
            return True
        except ADwinError:
            return False

    def _internal_to_status(self, value):
        '''
        Quality of life function to let the user know the status of a process instead of seeing a number
        '''
        if value == 0:
            return 'Not running'
        elif value == 1:
            return 'Running'
        else:
            return 'Being stopped'