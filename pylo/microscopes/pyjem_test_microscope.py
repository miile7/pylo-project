import time
import random

from PyJEM.offline.TEM3.apt3 import Apt3
from PyJEM.offline.TEM3.eos3 import EOS3
from PyJEM.offline.TEM3.feg3 import FEG3
from PyJEM.offline.TEM3.gun3 import GUN3
from PyJEM.offline.TEM3.lens3 import Lens3
from PyJEM.offline.TEM3.stage3 import Stage3

from .pyjem_microscope import PyJEMMicroscope

class PyJEMTestMicroscope(PyJEMMicroscope):
    def __init__(self, controller : "Controller") -> None:
        """Get the microscope instance"""
        super().__init__(controller)

        # force offline use
        self._lense_control = Lens3()
        self._stage = Stage3()
        self._eos = EOS3()
        self._feg = FEG3()
        self._gun = GUN3()
        self._aperture = Apt3()
    
    def setInLorentzMode(self, lorentz_mode: bool) -> None:
        # fake some hardware duration time
        time.sleep(random.random() * 2)
        super().setInLorentzMode(lorentz_mode)
    
    def setMeasurementVariableValue(self, id_: str, value: float) -> None:
        # fake some hardware duration time
        time.sleep(random.random() * 2)
        super().setMeasurementVariableValue(id_, value)
