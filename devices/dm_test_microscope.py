import time
import random

from pylo import loader
DMMicroscope = loader.getDeviceClass("Digital Micrograph Microscope")

class DMTestMicroscope(DMMicroscope):
    def __init__(self, *args, **kwargs) -> None:
        """Get the microscope instance"""
        super().__init__(*args, **kwargs)
        self._lorentz_mode = False
    
    def setInLorentzMode(self, lorentz_mode: bool) -> None:
        # fake some hardware duration time
        time.sleep(random.random())
        super().setInLorentzMode(lorentz_mode)
        self._lorentz_mode = lorentz_mode
    
    def getInLorentzMode(self) -> bool:
        return self._lorentz_mode
    
    def resetToSafeState(self) -> None:
        pass
    
    @staticmethod
    def defineConfigurationOptions(*args, **kwargs) -> None:
        DMMicroscope.defineConfigurationOptions(*args, **kwargs)
