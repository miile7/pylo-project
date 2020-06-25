import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import asyncio
import pytest
import random
import glob
import math
import time
import re

import pylo
import pylo.microscopes

def sleepRandomTime():
    respond_time = random.randrange(5, 20) / 50
    time.sleep(respond_time)
    return respond_time

class DummyMicroscope(pylo.microscopes.MicroscopeInterface):
    def __init__(self):
        super().__init__()

        self.supported_measurement_variables = [
            pylo.MeasurementVariable("focus", "Focus", 0, 10, "mA"),
            pylo.MeasurementVariable("magnetic-field", "Magnetic Field", 0, 3, "T"),
            pylo.MeasurementVariable("x-tilt", "Tilt (x direction)", -35, 35, "deg")
        ]

        self.is_in_lorenz_mode = False
        self.is_in_safe_state = False

        self.focus = 0
        self.magnetic_field = 0
        self.x_tilt = 0
    
    async def setMeasurementVariableValue(self, id_, value):
        if not self.isValidMeasurementVariableValue(id_, value):
            variable = self.getMeasurementVariableById(id_)

            raise ValueError(
                ("The measurement variable {} has to be in the range " + 
                 "{} <= val <= {}, but it is {}.").format(id_, 
                 variable.min_value, variable.max_value, value)
            )

        self.is_in_safe_state = False
        respond_time = sleepRandomTime()

        # simulate small variance in real value in first or second digit after 
        # decimal separator
        # value += (random.random() - 0.5) / 10

        if id_ == "focus":
            self.focus = value
        elif id_ == "magnetic-field":
            self.magnetic_field = value
        elif id_ == "x-tilt":
            self.x_tilt = value
        else:
            raise KeyError("The measurement variable {} does not exist.".format(id_))

    async def getMeasurementVariableValue(self, id_):
        respond_time = sleepRandomTime()

        if id_ == "focus":
            return self.focus
        elif id_ == "magnetic-field":
            return self.magnetic_field
        elif id_ == "x-tilt":
            return self.x_tilt
        else:
            raise KeyError("The measurement variable {} does not exist.".format(id_))
    
    async def setInLorenzMode(self, lorenz_mode):
        respond_time = sleepRandomTime()

        if lorenz_mode:
            self.is_in_safe_state = False
        
        self.is_in_lorenz_mode = lorenz_mode
    
    async def getInLorenzMode(self):
        respond_time = sleepRandomTime()

        return self.is_in_lorenz_mode
    
    async def resetToSafeState(self):
        respond_time = sleepRandomTime()
        
        self.is_in_safe_state = True

class DummyCamera(pylo.CameraInterface):
    def __init__(self, microscope):
        super().__init__()
        self.microscope = microscope
        self.img_count = 0
        self.is_in_safe_state = False
    
    async def resetToSafeState(self):
        respond_time = sleepRandomTime()
        
        self.is_in_safe_state = True
    
    async def recordImage(self):
        self.is_in_safe_state = False
        size = max(4, len(self.microscope.supported_measurement_variables))
        # create grayscale image
        image_data = np.zeros((size, size), dtype=np.uint8)

        # save current image count first row in the first two pixels in the 
        # image
        image_data[0][0] = math.floor(self.img_count / 255)
        image_data[0][1] = self.img_count % 255

        # save current focus second row in the image, normed by min and max 
        # value
        f_var = self.microscope.getMeasurementVariableById("focus")
        image_data[1][0] = ((self.microscope.focus - f_var.min_value) / 
                            (f_var.max_value - f_var.min_value) * 255)

        # save the magnetic field
        m_var = self.microscope.getMeasurementVariableById("magnetic-field")
        image_data[2][0] = ((self.microscope.magnetic_field - m_var.min_value) / 
                            (m_var.max_value - m_var.min_value) * 255)

        # save the magnetic field
        t_var = self.microscope.getMeasurementVariableById("x-tilt")
        image_data[3][0] = ((self.microscope.x_tilt - t_var.min_value) / 
                            (t_var.max_value - t_var.min_value) * 255)
        
        respond_time = sleepRandomTime()

        tags = {
            "exposure-time": respond_time,
            "image-count": self.img_count,
            "camera": "DummyCamera for testing"
        }

        self.img_count += 1

        return pylo.Image(image_data, tags)

class DummyConfiguration(pylo.AbstractConfiguration):
    def __init__(self):
        super().__init__()
    
    def loadConfiguration(self):
        pass
    
    def saveConfiguration(self):
        pass

class DummyController:
    def __init__(self):
        self.microscope = DummyMicroscope()
        self.camera = DummyCamera(self.microscope)
        self.configuration = DummyConfiguration()

class TestMeasurement:
    def setup_method(self):
        self.root = os.path.join(os.path.dirname(__file__), "tmp_test_files")

        if not os.path.exists(self.root):
            os.mkdir(self.root, 0o760)

        self.controller = DummyController()
        self.measurement_steps = []

        for f in (0, 5, 10):
            for m in (0, 1, 2):
                for t in (-10, 0, 10):
                    self.measurement_steps.append({"focus": f, 
                                                   "magnetic-field": m, 
                                                   "x-tilt": t})

        self.measurement = pylo.Measurement(self.controller, self.measurement_steps)
        self.measurement.save_dir = self.root
        self.measurement.name_format = "{counter}-dummy-measurement.tif"

        # register events

        asyncio.run(self.measurement.start())
    
    def teardown_method(self):
        # for f in os.listdir(self.root):
        #     os.remove(os.path.join(self.root, f))
        
        # os.removedirs(self.root)
        pass
    
    def test_all_steps_produced_images(self):
        """Test if there are as much image files in the directory as there are 
        steps to record images for."""

        reg = re.compile(r"[\d]+-dummy-measurement\.tif")
        file_count = 0

        for f in glob.glob("*-dummy-measurement.tif"):
            if reg.match(f):
                file_count += 1
        
        assert file_count == len(self.measurement_steps)
    
    def throw_exception(self):
        raise Exception("This is an exception to test whether exceptions are " + 
                        "handled correctly.")

    @pytest.mark.skip()
    def test_exception_stops_measurement(self):
        """Test if an exception stops the measurement."""
        pylo.after_record.append(self.throw_exception)
