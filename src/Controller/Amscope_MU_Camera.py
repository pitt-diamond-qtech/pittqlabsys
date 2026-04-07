# CREATED JANNET TRABELSI ON 10/03/2025
# USED AMCAM THAT COMMUNICATES WITH THE CAMERA THROUGH THE DLL FILE
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

from __future__ import annotations
#from src.Controller import amcam
from src.Controller import toupcam
from src.core import Device,Parameter
from src.core.struct_hdf5 import save_parameters_hdf5

_DEFAULT_AUTO_EXPOSURE_TARGET  = 120
_DEFAULT_TEMP = 6503
_DEFAULT_TINT = 1000
_DEFAULT_LEVEL_RANGE = 125
_DEFAULT_CONTRAST = 0
_DEFAULT_HUE = 0
_DEFAULT_SATURATION = 128
_DEFAULT_BRIGHTNESS = 0
_DEFAULT_GAMMA = 100
_DEFAULT_WHITE_BALANCE_GAIN = 0
_DEFAULT_GAIN = 100
_DEFAULT_EXPOSURE_TIME_US = 10000
_MIN_EXPOSURE_TIME = 244
_MAX_EXPOSURE_TIME = 2000000 # or 350000 what i got from get_MaxAutoExpoTimeAGain
_MIN_BRIGHTNESS = -255
_MAX_BRIGHTNESS = 255
_MIN_SATURATION = 0
_MAX_SATURATION = 255
_MIN_CONTRAST = -255
_MAX_CONTRAST = 255
TOUPCAM_EXPOGAIN_MIN              = 100      # exposure gain, minimum value
TOUPCAM_EXPOGAIN_MAX              = 500      # exposure gain, max value
TOUPCAM_WBGAIN_MIN                = -127     # white balance gain
TOUPCAM_WBGAIN_MAX                = 127      # white balance gain
_DEFAULT_RESOLUTION = "low"
_server_port = 5005

TOUPCAM_TEMP_MIN                  = 2000     # color temperature, minimum value
TOUPCAM_TEMP_MAX                  = 15000    # color temperature, maximum value
TOUPCAM_TINT_MIN                  = 200      # tint
TOUPCAM_TINT_MAX                  = 2500     # tint
TOUPCAM_HUE_MIN                   = -180     # hue
TOUPCAM_HUE_MAX                   = 180      # hue
TOUPCAM_GAMMA_MIN                 = 20       # gamma
TOUPCAM_GAMMA_MAX                 = 180      # gamma
TOUPCAM_AETARGET_MIN              = 16       # target of auto exposure
TOUPCAM_AETARGET_MAX              = 220      # target of auto exposure

class Amscope_MU_Camera(Device):
    """This class implements the Windfreak SynthUSBII. The device plugs into a usb port and is communicated with using pyvisa."""
    _DEFAULT_SETTINGS = Parameter(Device._get_base_settings() +[
        Parameter('exposure gain', _DEFAULT_GAIN, int, 'camera exposure gain', min_value = TOUPCAM_EXPOGAIN_MIN, max_value = TOUPCAM_EXPOGAIN_MAX),
        Parameter('exposure time', _DEFAULT_EXPOSURE_TIME_US, int, 'camera exposure time in us', min_value = _MIN_EXPOSURE_TIME, max_value = _MAX_EXPOSURE_TIME),
        Parameter('brightness', _DEFAULT_BRIGHTNESS, int, 'camera brightness', min_value = _MIN_BRIGHTNESS, max_value = _MAX_BRIGHTNESS),
        Parameter('saturation', _DEFAULT_SATURATION, int, 'camera saturation', min_value = _MIN_SATURATION, max_value = _MAX_SATURATION),
        Parameter('contrast', _DEFAULT_CONTRAST, int, 'camera contrast', min_value = _MIN_CONTRAST, max_value = _MAX_CONTRAST),
        Parameter('Gamma', _DEFAULT_GAMMA, int, 'camera Gamma', min_value = TOUPCAM_GAMMA_MIN, max_value = TOUPCAM_GAMMA_MAX),
        Parameter('Temp', _DEFAULT_TEMP, int, 'camera Temp', min_value = TOUPCAM_TEMP_MIN, max_value = TOUPCAM_TEMP_MAX),
        Parameter('Tint', _DEFAULT_TINT, int, 'camera Tint', min_value = TOUPCAM_TINT_MIN, max_value = TOUPCAM_TINT_MAX),
        Parameter('Hue', _DEFAULT_HUE, int, 'camera Hue', min_value = TOUPCAM_HUE_MIN, max_value = TOUPCAM_HUE_MAX),
        Parameter('server_port', _server_port, int, 'server_port'),
        # _DEFAULT_AUTO_EXPOSURE_TARGET = 120
        # _DEFAULT_LEVEL_RANGE = 125
    ])

    def update(self, settings):
        """
        Updates the internal settings of the camera
        Args:
            settings: a dictionary in the standard settings format
        """
        super(Amscope_MU_Camera, self).update(settings)
        for key, value in settings.items():
            if not (key == 'server_port'):
                if key == 'exposure gain':
                    self.set_ExpoAGain(value)
                elif key == 'exposure time':
                    lo, hi, _ = self.amscope_cam.get_ExpTimeRange()
                    self.put_ExpoTime(value)
                elif key == 'brightness':
                    self.put_Brightness(value)
                elif key == 'saturation':
                    self.put_Saturation(value)
                elif key == 'contrast':
                    self.put_Contrast(value)
                elif key == 'Gamma':
                    self.put_Gamma(value)
                elif key == 'Temp':
                    _, tint = self.amscope_cam.get_TempTint()
                    self.put_TempTint(value, tint)
                elif key == 'Tint':
                    temp, _ = self.amscope_cam.get_TempTint()
                    self.put_TempTint(temp, value)
                elif key == 'Hue':
                    self.put_Hue(value)

    @property
    def _PROBES(self):
        return {
            'get_data': 'choose whether you need to get data from this device or not',
            'exposure gain': 'exposure gain',
            'exposure time': 'exposure time',
            'Gamma': 'Gamma',
            'Chrome': 'Chrome',
            'VFlip': 'VFlip',
            'HFlip': 'HFlip',
            'Negative': 'Negative',
            'Speed': 'Speed',
            'HZ': 'HZ',
            'Mode': 'Mode',
            'Temp': 'Temp',
            'Tint': 'Tint',
            'AWBAuxRect': 'AWBAuxRect',
            'AEAuxRect': 'AEAuxRect',
            'BlackBalance': 'BlackBalance',
            'ABBAuxRect': 'ABBAuxRect',
            'Hue': 'Hue',
            'brightness': 'brightness',
            'saturation': 'saturation',
            'contrast': 'contrast'
        }

    def return_min_max(self, name):
        if name == 'exposure gain':
            return TOUPCAM_EXPOGAIN_MIN, TOUPCAM_EXPOGAIN_MAX
        elif name == 'exposure time':
            return _MIN_EXPOSURE_TIME, _MAX_EXPOSURE_TIME
        elif name == 'brightness':
            return _MIN_BRIGHTNESS, _MAX_BRIGHTNESS
        elif name == 'saturation':
            return _MIN_SATURATION, _MAX_SATURATION
        elif name == 'contrast':
            return _MIN_CONTRAST, _MAX_CONTRAST
        elif name == 'Gamma':
            return TOUPCAM_GAMMA_MIN, TOUPCAM_GAMMA_MAX
        elif name == 'Temp':
            return TOUPCAM_TEMP_MIN, TOUPCAM_TEMP_MAX
        elif name == 'Tint':
            return TOUPCAM_TINT_MIN, TOUPCAM_TINT_MAX
        elif name == 'Hue':
            return TOUPCAM_HUE_MIN, TOUPCAM_HUE_MAX

    def _param_to_internal(self, param):
        # converts settings parameter to corresponding key
        if param not in ['exposure gain', 'exposure time', 'Gamma', 'Chrome', 'VFlip',
                             'HFlip',
                             'Negative', 'Speed', 'HZ', 'Mode', 'Temp', 'Tint', 'AWBAuxRect', 'AEAuxRect',
                             'BlackBalance',
                             'ABBAuxRect', 'Hue', 'brightness', 'saturation', 'contrast']:
            raise KeyError
        return param

    def read_probes(self, key):
        assert (self._settings_initialized)
        assert key in list(self._PROBES.keys())

        key_internal = self._param_to_internal(key)
        if key == 'exposure gain':
            value = self.amscope_cam.get_ExpoAGain()
        elif key == 'get_data':
            return self.settings['get_data']
        elif key == 'exposure time':
            value = self.amscope_cam.get_ExpoTime()
        elif key == 'Gamma':
            value = self.amscope_cam.get_Gamma()
        elif key == 'Chrome':
            value = self.amscope_cam.get_Chrome()
        elif key == 'VFlip':
            value = self.amscope_cam.get_VFlip()
        elif key == 'HFlip':
            value = self.amscope_cam.get_HFlip()
        elif key == 'Negative':
            value = self.amscope_cam.get_Negative()
        elif key == 'Speed':
            value = self.amscope_cam.get_Speed()
        elif key == 'HZ':
            value = self.amscope_cam.get_HZ()
        elif key == 'Mode':
            value = self.amscope_cam.get_Mode()
        elif key == 'Temp':
            temp, _ = self.amscope_cam.get_TempTint()
            value = temp
        elif key == 'Tint':
            _, tint = self.amscope_cam.get_TempTint()
            value = tint
        elif key == 'AWBAuxRect':
            value = self.amscope_cam.get_AWBAuxRect()
        elif key == 'AEAuxRect':
            value = self.amscope_cam.get_AEAuxRect()
        elif key == 'BlackBalance':
            value = self.amscope_cam.get_BlackBalance()
        elif key == 'ABBAuxRect':
            value = self.amscope_cam.get_ABBAuxRect()
        elif key == 'Hue':
            value = self.amscope_cam.get_Hue()
        elif key == 'brightness':
            value = self.amscope_cam.get_Brightness()
        elif key == 'saturation':
            value = self.amscope_cam.get_Saturation()
        elif key == 'contrast':
            value = self.amscope_cam.get_Contrast()
        return value

    @property
    def is_connected(self):
        try:
            self._ask_value('f')  # arbitrary call to check connection
            return True
        except Exception as e:
            print(self, e)
            return False

    def close(self):
        self.amscope_cam.Close()

    def __init__(self, name=None, settings=None):
        # the object of Amcam must be obtained by classmethod Open or OpenByIndex, it cannot be obtained by obj = amcam.Amcam()
        ###cams = amcam.Amcam.EnumV2()
        cams = toupcam.Toupcam.EnumV2()
        if not cams:
            print("no camera found")

        try:
            ###self.amscope_cam = amcam.Amcam.Open(cams[0].id)
            self.amscope_cam = toupcam.Toupcam.Open(cams[0].id) # future programmers: to add more cameras, you can have cams[1], cams[2], etc
        ###except amcam.HRESULTException as ex:
        except toupcam.HRESULTException as ex:
            print("failed to open camera", ex)
            return

        self.name = "Amscope Camera"
        super(Amscope_MU_Camera, self).__init__(name, settings)
        self.amscope_cam.put_ExpoAGain(_DEFAULT_GAIN)
        lo, hi, _ = self.amscope_cam.get_ExpTimeRange()
        self.amscope_cam.put_ExpoTime(max(lo, min(_DEFAULT_EXPOSURE_TIME_US, hi)))
        self.amscope_cam.put_eSize(2)
        self.w, self.h = self.amscope_cam.get_Size()

    def set_ExpoAGain(self,gain):
        if not TOUPCAM_EXPOGAIN_MIN <= gain <= TOUPCAM_EXPOGAIN_MAX:
            raise KeyError
        self.amscope_cam.put_ExpoAGain(gain)

    def get_ExpTimeRange(self):
        return self.amscope_cam.get_ExpTimeRange()

    def put_ExpoTime(self, t):
        if not _MIN_EXPOSURE_TIME <= t <= _MAX_EXPOSURE_TIME:
            raise KeyError
        self.amscope_cam.put_ExpoTime(t)

    def put_Brightness(self, brightness):
        if not _MIN_BRIGHTNESS <= brightness <= _MAX_BRIGHTNESS:
            raise KeyError
        self.amscope_cam.put_Brightness(brightness)

    def put_Saturation(self, saturation):
        if not _MIN_SATURATION <= saturation <= _MAX_SATURATION:
            raise KeyError
        self.amscope_cam.put_Saturation(saturation)

    def put_Contrast(self, contrast):
        if not _MIN_CONTRAST <= contrast <= _MAX_CONTRAST:
            raise KeyError
        self.amscope_cam.put_Contrast(contrast)

    def put_eSize(self, size):
        self.amscope_cam.put_eSize(size)

    def get_Size(self):
        return self.amscope_cam.get_Size()

    def get_AutoExpoEnable(self):
        return self.amscope_cam.get_AutoExpoEnable()

    def put_AutoExpoEnable(self, en):
        """
        bAutoExposure:
           0: disable auto exposure
           1: auto exposure continue mode
           2: auto exposure once mode
        """
        if en not in [0, 1, 2, "0", "1", "2"]:
            raise KeyError
        self.amscope_cam.put_AutoExpoEnable(int(en))

    def StartPullModeWithCallback(self, A, B):
        self.amscope_cam.StartPullModeWithCallback(A, B)

    def PullImageV2(self, a, b, c):
        self.amscope_cam.PullImageV2(a, b, c)

    def set_WhiteBalanceGain(self, value):
        if not TOUPCAM_WBGAIN_MIN <= value <=TOUPCAM_WBGAIN_MAX:
            raise KeyError
        self.amscope_cam.put_WhiteBalanceGain(value)

    def put_TempTint(self, nTemp, nTint):
        if not TOUPCAM_TEMP_MIN <= nTemp <= TOUPCAM_TEMP_MAX:
            raise KeyError
        if not TOUPCAM_TINT_MIN <= nTint <= TOUPCAM_TINT_MAX:
            raise KeyError
        self.amscope_cam.put_TempTint(nTemp, nTint)

    def put_Gamma(self, gamma):
        if not TOUPCAM_GAMMA_MIN <= gamma <= TOUPCAM_GAMMA_MAX:
            raise KeyError
        self.amscope_cam.put_Gamma(gamma)

    def put_Hue(self, hue):
        if not TOUPCAM_HUE_MIN <= hue <= TOUPCAM_HUE_MAX:
            raise KeyError
        self.amscope_cam.put_Hue(hue)

    def stop(self):
        self.amscope_cam.Stop()

    def pause(self, enable):
        self.amscope_cam.Pause(enable)

if __name__ == '__main__':
    am=Amscope_MU_Camera() # 350000, 244
    print(am.get_Size())
    print(f"get_MaxAutoExpoTimeAGain {am.amscope_cam.get_MaxAutoExpoTimeAGain()}")