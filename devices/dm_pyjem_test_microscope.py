import time
import random

from pylo import loader
DMPyJEMMicroscope = loader.getDeviceClass("DM + PyJEM Microscope")

class DMPyJEMTestMicroscope(DMPyJEMMicroscope):
    def __init__(self, *args, **kwargs) -> None:
        """Get the microscope instance"""
        self._lorentz_mode = False
        super().__init__(*args, **kwargs)

        self.pyjem_olcurrent_args += ["--debug"]
    
    def setInLorentzMode(self, lorentz_mode: bool) -> None:
        # fake some hardware duration time
        time.sleep(random.random())
        super().setInLorentzMode(lorentz_mode)
        self._lorentz_mode = lorentz_mode
    
    def getInLorentzMode(self) -> bool:
        return self._lorentz_mode
    
    def resetToSafeState(self) -> None:
        try:
            import DigitalMicrograph as DM
        except Exception:
            DM = None
        
        text = "Setting {} to safe state!".format(self.__class__.__name__)
        if DM is not None:
            DM.OkDialog(text)
        else:
            print(text)
    
    # def _setXTilt(self, angle, *args, **kwargs):
    #     if angle > 10:
    #         raise AssertionError("This is a test error caused by an x angle > 10 deg")
        
    #     super()._setXTilt(angle, *args, **kwargs)
    
    @staticmethod
    def defineConfigurationOptions(*args, **kwargs) -> None:
        DMPyJEMMicroscope.defineConfigurationOptions(*args, **kwargs)
