import time
import random

from pylo import Datatype
from pylo import MicroscopeInterface
from pylo import MeasurementVariable

class DummyMicroscope(MicroscopeInterface):
    """This class represents a dummy microscope.

    Attributes
    ----------
    record_time : int or None
        The record time in seconds or None for random times (between 0 and 1)
    """

    def __init__(self, *args, **kwargs) -> None:
        """Create a new camera interface object."""
        super().__init__(*args, **kwargs)
        self.record_time = None
        self._values = {}
        self.lorentz_mode = False

        self.supports_parallel_measurement_variable_setting = False

        self.registerMeasurementVariable(
            MeasurementVariable("focus", "Focus", 0, 100, "nm", Datatype.int, 3),
            lambda: self._getVal("focus"), lambda x: self._setVal("focus", x)
        )
        var = self.registerMeasurementVariable(
            MeasurementVariable("ol-current", "Objective lens current", 0, 
                                0x800, "hex", Datatype.hex_int),
            lambda: self._getVal("ol-current"), 
            lambda x: self._setVal("ol-current", x)
        )
        var.default_step_width_value = 0x300
        var.default_end_value = 0x600

        self.registerMeasurementVariable(
            MeasurementVariable("pressure", "Pressure", 51, 3060, "Pa", 
                                Datatype.int, 1/1020, None, "bar", "Atmospheres", 
                                calibrated_format=float),
            lambda: self._getVal("pressure"), 
            lambda x: self._setVal("pressure", x)
        )

        self.setMeasurementVariableValue("focus", random.randint(0, 100))
        self.setMeasurementVariableValue("ol-current", random.randint(0, 0x800))
        self.setMeasurementVariableValue("pressure", random.randint(51, 3060))
    
    def _setVal(self, id_, value):
        if isinstance(self.record_time, (int, float)):
            if self.record_time >= 0:
                time.sleep(self.record_time)
        else:
            time.sleep(random.random())

        self._values[id_] = value
    
    def _getVal(self, id_):
        if id_ in self._values:
            return self._values[id_]
        else:
            return 0
    
    def setInLorentzMode(self, lorentz_mode):
        self.lorentz_mode = lorentz_mode
    
    def getInLorentzMode(self, lorentz_mode):
        return self.lorentz_mode
    
    def resetToSafeState(self) -> None:
        pass