from src.core import Device, Parameter
import matlab.engine
eng = matlab.engine.start_matlab()

class coherent_899_dye_laser(Device):
    _DEFAULT_SETTINGS = Parameter(Device._get_base_settings() +[
        Parameter('wavelength', 594, list(range(567, 625)) ,'wavelength in nm'),
        Parameter('position', 594, list(range(567, 625)) ,'position'),
    ])

    def __init__(self, name=None, settings=None):
        super(coherent_899_dye_laser, self).__init__(name, settings)
        try:
            self._connect()
        except Exception as e:
            raise e

    def update(self, settings: dict):
        super(coherent_899_dye_laser, self).update(settings)
        for key, value in settings.items():
            #if not (key == 'port' or key == 'GPIB_num'):
            if self.settings.valid_values[
                key] == bool:  # converts booleans, which are more natural to store for on/off, to
                value = int(value)  # the integers used internally in the laser
            key = self._param_to_internal(key)
            # only send update to Device if connection to Device has been established
            if self._settings_initialized:
                if key == "wavelength":
                    self.eng.coherent_899_dye_client_gotowavelengthfast(float(value))
                elif key == "position":
                    self.eng.coherent_899_dye_client_gotoposition(float(value))

    def _param_to_internal(self, param):
        return param

    def read_probes(self, key=None):
        assert (
            self._settings_initialized)  # will cause read_probes to fail if settings (and thus also connection) not yet initialized
        assert key in list(self._PROBES.keys())
        key_internal = self._param_to_internal(key)
        if key_internal == "wavelength":
            value = self.eng.coherent_899_dye_client_getwavelength
        elif key == 'get_data':
            return self.settings['get_data']
        elif key_internal == "power":
            value = self.eng.coherent_899_dye_client_getpower
        elif key_internal == "position":
            value = self.eng.coherent_899_dye_client_getposition
        elif key_internal == "calibration":
            value = self.eng.coherent_899_dye_client_getcalibration
        else:
            raise NotImplementedError
        return value

    @property
    def _PROBES(self):
        return {
            'get_data': 'choose whether you need to get data from this device or not',
            'wavelength': 'wavelength',
            'position': 'position',
            'power': 'power',
            'calibration': 'calibration',
        }

    def _connect(self):
        self.eng = matlab.engine.start_matlab()
        # Add folder containing the client functions
        self.eng.addpath(
            r"D:\software_by_our_lab\working\main_gui\basic_libaries\coherent_899_ring_dye_laser\client_functions",
            nargout=0)
        # Add folder containing the server helper function
        self.eng.addpath(
            r"D:\software_by_our_lab\working\main_gui\basic_libaries\coherent_899_ring_dye_laser\server_functions",
            nargout=0)
        # Call the function directly
        try:
            ret = self.eng.coherent_899_sendmsgtoserver('identify', nargout=1)
            print("Server response:", ret)
        except matlab.engine.MatlabExecutionError as e:
            print("Error communicating with laser server:", e)
        return 0

    def close(self):
        self.eng.coherent_899_dye_client_findinstrument('close')
        self.eng.coherent_899_sendmsgtoserver('turn off')
        # Quit MATLAB engine
        self.eng.quit()
        print('dye laser closed')

if __name__ == "__main__":
    dye_laser = coherent_899_dye_laser()
    dye_laser.close()