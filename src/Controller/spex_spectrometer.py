from src.core import Device, Parameter
import matlab.engine
eng = matlab.engine.start_matlab()

class spex_spectrometer(Device):
    _DEFAULT_SETTINGS = Parameter(Device._get_base_settings() +[
        Parameter('wavelength', 594, float ,'wavelength in nm'),
        Parameter('grating', 1, int ,'grating'),
        Parameter('mirror', 1, int, 'mirror'),
        Parameter('gain', 1.5, float, 'gain'),
        Parameter('inttime', 1, int, 'inttime'),
        Parameter('startlive', 1, int, 'startlive'),
        Parameter('stoplive', 1, int, 'stoplive'),

    ])

    def __init__(self, name=None, settings=None):
        super(spex_spectrometer, self).__init__(name, settings)
        self.andor_camera = None
        self.eng = None
        self.spectrometer = None
        try:
            self._connect()
        except Exception as e:
            raise e

    def update(self, settings: dict):
        super(spex_spectrometer, self).update(settings)
        for key, value in settings.items():
            #if not (key == 'port' or key == 'GPIB_num'):
            if self.settings.valid_values[
                key] == bool:  # converts booleans, which are more natural to store for on/off, to
                value = int(value)  # the integers used internally in the laser
            key = self._param_to_internal(key)
            # only send update to Device if connection to Device has been established
            if self._settings_initialized:
                if key == "wavelength":
                    self.eng.feval(self.spectrometer['gotowavelength'], float(value))
                elif key == "grating":
                    self.eng.feval(self.spectrometer['gotograting'], float(value))
                elif key == "mirror":
                    self.eng.feval(self.spectrometer['gotomirror'], int(value))
                elif key == "gain":
                    self.eng.feval(self.andor_camera['setgain'], float(value))
                elif key == "inttime":
                    self.eng.feval(self.andor_camera['setinttime'], int(value))
                elif key == "startlive":
                    self.eng.feval(self.andor_camera['startlive'])
                elif key == "stoplive":
                    self.eng.feval(self.andor_camera['stoplive'])
                else:
                    raise ValueError("Unknown key '%s'" % key)

    def _param_to_internal(self, param):
        return param

    def read_probes(self, key=None):
        assert (
            self._settings_initialized)  # will cause read_probes to fail if settings (and thus also connection) not yet initialized
        assert key in list(self._PROBES.keys())
        key_internal = self._param_to_internal(key)
        if key_internal == "grating":
            value = self.eng.feval(self.spectrometer['getgrating'])
        elif key == 'get_data':
            return self.settings['get_data']
        elif key_internal == "gratings":
            value = self.eng.feval(self.spectrometer['getgratings'])
        elif key_internal == "mirror":
            value = self.eng.feval(self.spectrometer['getmirror'])
        elif key_internal == "mirrors":
            value = self.eng.feval(self.spectrometer['getmirrors'])
        elif key_internal == "mirror_number":
            value = self.eng.feval(self.spectrometer['getmirror_number'])
        elif key_internal == "spectrometer_name":
            value = self.eng.feval(self.spectrometer['getname'])
        elif key_internal == "wavelength":
            value = self.eng.feval(self.spectrometer['getwavelength'])
        elif key_internal == "repeatability_tolerance":
            value = self.eng.feval(self.spectrometer['getrepeatabilitytolerance'])
        elif key_internal == "specific_name":
            value = self.eng.feval(self.andor_camera['specific_name'])
        elif key_internal == "gain":
            value = self.eng.feval(self.andor_camera["getgain"])
        elif key_internal == "gainlimits":
            value = self.eng.feval(self.andor_camera['getgainlimits'])
        elif key_internal == "image":
            value = self.eng.feval(self.andor_camera['getimage'])
        elif key_internal == "fast_image":
            value = self.eng.feval(self.andor_camera['getimagefast'])
        elif key_internal == "inttime":
            value = self.eng.feval(self.andor_camera['getinttime'])
        elif key_internal == "maxpixelvalue":
            value = self.eng.feval(self.andor_camera['getmaxpixelvalue'])
        elif key_internal == "pixelwarninglevel":
            value = self.eng.feval(self.andor_camera['getpixelwarninglevel'])
        elif key_internal == "resolution":
            value = self.eng.feval(self.andor_camera['getresolution'])
        else:
            raise NotImplementedError
        return value

    @property
    def _PROBES(self):
        return {
            'get_data': 'choose whether you need to get data from this device or not',
            'grating': 'grating',
            'gratings': 'gratings',
            'mirror': 'mirror',
            'mirror_number': 'mirror_number',
            'mirrors': 'mirrors',
            'spectrometer_name':'spectrometer_name',
            'wavelength': 'wavelength',
            'repeatability_tolerance': 'repeatability_tolerance',
            'specific_name': 'specific_name',
            'gain': 'gain',
            'gainlimits': 'gainlimits',
            'image': 'image',
            'fast_image': 'fast_image',
            'inttime': 'inttime',
            'maxpixelvalue': 'maxpixelvalue',
            'pixelwarninglevel': 'pixelwarninglevel',
            'resolution': 'resolution'
        }

    def _connect(self):
        self.eng = matlab.engine.start_matlab()
        # Add folder containing the client functions
        self.eng.addpath(
            r"D:\software_by_our_lab\working\main_gui\basic_libaries\dutt_lab_remote_spectrometer\client_functions",
            nargout=0)
        # Add folder containing the server helper function
        self.eng.addpath(
            r"D:\software_by_our_lab\working\main_gui\basic_libaries\dutt_lab_remote_spectrometer\server_functions",
            nargout=0)
        self.eng.addpath(r"D:\software_by_our_lab\working\main_gui\basic_libaries\dutt_lab_remote_spectrometer")
        # Call the function directly
        try:
            ret = self.eng.DLRS_spectrometer_findinstrument()
            print("Server response:", ret)
            self.andor_camera = self.eng.DLRS_camera_create_device_class() #
            self.spectrometer = self.eng.DLRS_spectrometer_create_device_class() #
        except matlab.engine.MatlabExecutionError as e:
            print("Error communicating with spectrometer server:", e)
        return 0

    def close(self):
        print(self.eng.DLRS_sendmsgtoserver('turn_off'))
        # Quit MATLAB engine
        self.eng.quit()
        print('spectrometer closed')

    def close_camera(self):
        self.eng.feval(self.andor_camera['closeinstrument'])

if __name__ == "__main__":
    s=spex_spectrometer()
    s.update({"gain": 1.5})
    print('hello i ran')
    print(s.read_probes("gain"))
    s.close()