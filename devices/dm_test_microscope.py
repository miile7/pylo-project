import time
import random

from pylo import loader
DMMicroscope = loader.getDeviceClass("Digital Micrograph Microscope")

class DMTestMicroscope(DMMicroscope):
    def __init__(self, *args, **kwargs) -> None:
        """Get the microscope instance"""
        self._lorentz_mode = False
        super().__init__(*args, **kwargs)
    
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
    
    @staticmethod
    def defineConfigurationOptions(*args, **kwargs) -> None:
        DMMicroscope.defineConfigurationOptions(*args, **kwargs)
