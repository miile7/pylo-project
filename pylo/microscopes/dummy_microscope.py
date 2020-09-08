import time
import random

from .pyjem_microscope import PyJEMMicroscope

class DummyMicroscope(PyJEMMicroscope):
    def setMeasurementVariableValue(self, id_: str, value: float) -> None:
        time.sleep(random.random() * 2)
        super().setMeasurementVariableValue(id_, value)
