import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PIL import Image as PILImage
import numpy as np
import datetime
import pytest
import random
import copy
import glob
import math
import time
import csv
import re

import pylo
pylo.config.ENABLED_PROGRAM_LOG_LEVELS = []

from pylotestlib import DummyView
from pylotestlib import DummyConfiguration

class DummyController(pylo.Controller):
    def __init__(self, *args, **kwargs):
        super().__init__(DummyView(), DummyConfiguration())
        self.microscope = DummyMicroscope(self)
        self.camera = DummyCamera(self)

sleep_time = "random"
def setSleepTime(time="random"):
    global sleep_time
    sleep_time = time

def sleepRandomTime():
    global sleep_time
    if isinstance(sleep_time, (int, float)):
        respond_time = sleep_time
    else:
        respond_time = random.randrange(5, 20) / 50
    time.sleep(respond_time)
    return respond_time

def convertMeasurementVariableToImageSave(var, value, steps=255):
    """Convert the measurement variable `var` with the `value` to be saved in 
    an image with `steps` values in one pixel.

    Parameters
    ----------
    var : pylo.MeasurementVariable
        The measurement variable which defines the min and max values
    value : float
        The value to convert
    steps : int, optional
        The number of value steps per pixel
    
    Returns
    -------
    float
        The value divided on `steps`
    """
    return (value - var.min_value) / (var.max_value - var.min_value) * steps

def convertImageSaveToMeasurementVariable(var, value, steps=255):
    """Convert the saved measurement variable `var` with the image pixel 
    `value` back to the original value (note that the conversion is not 
    precise, there is some data lost which makes the value to be roughly the 
    original value).

    Parameters
    ----------
    var : pylo.MeasurementVariable
        The measurement variable which defines the min and max values
    value : float
        The converted value
    steps : int, optional
        The number of value steps per pixel
    
    Returns
    -------
    float
        The value of the measurement variable
    """
    return value / steps * (var.max_value - var.min_value) + var.min_value

class DummyMicroscope(pylo.MicroscopeInterface):
    def __init__(self, controller):
        super().__init__(controller)

        self.supported_measurement_variables = [
            pylo.MeasurementVariable("focus", "Focus", 0, 10, "mA"),
            pylo.MeasurementVariable("lens-current", "OM Current", 0, 3, 
                                     format=pylo.Datatype.hex_int,
                                     calibration=2, calibrated_unit="T",
                                     calibrated_name="Magnetic Field"),
            pylo.MeasurementVariable("x-tilt", "Tilt (x direction)", -35, 35, "deg")
        ]

        self.measurement_variable_set_log = []
        
        self.is_in_lorentz_mode = False
        self.is_in_safe_state = False

        self.focus = 0
        self.magnetic_field = 0
        self.x_tilt = 0

        # the measurement variable that is currently being set, this is for
        # testing that the stop event prevents all actions from finishing
        self.currently_setting_measurement_variable = None
    
    def setMeasurementVariableValue(self, id_, value):
        self.currently_setting_measurement_variable = id_
        if not self.isValidMeasurementVariableValue(id_, value):
            variable = self.getMeasurementVariableById(id_)

            raise ValueError(
                ("The measurement variable {} has to be in the range " + 
                 "{} <= val <= {}, but it is {}.").format(id_, 
                 variable.min_value, variable.max_value, value)
            )

        # self.is_in_safe_state = False
        sleepRandomTime()

        # simulate small variance in real value in first or second digit after 
        # decimal separator
        # value += (random.random() - 0.5) / 10

        if id_ == "focus":
            self.focus = value
        elif id_ == "lens-current":
            self.magnetic_field = value
        elif id_ == "x-tilt":
            self.x_tilt = value
        else:
            raise KeyError("The measurement variable {} does not exist.".format(id_))
        
        self.measurement_variable_set_log.append(({"focus": self.focus,
                                                   "lens-current": self.magnetic_field,
                                                   "x-tilt": self.x_tilt},
                                                   time.time()))
            
        self.currently_setting_measurement_variable = None
        self.currently_setting_lorentz_mode = False

    def getMeasurementVariableValue(self, id_):
        sleepRandomTime()

        if id_ == "focus":
            return self.focus
        elif id_ == "lens-current":
            return self.magnetic_field
        elif id_ == "x-tilt":
            return self.x_tilt
        else:
            raise KeyError("The measurement variable {} does not exist.".format(id_))
    
    def setInLorentzMode(self, lorentz_mode):
        self.currently_setting_lorentz_mode = True
        sleepRandomTime()

        # if lorentz_mode:
        #     self.is_in_safe_state = False
        
        self.is_in_lorentz_mode = lorentz_mode
        self.currently_setting_lorentz_mode = False
    
    def getInLorentzMode(self):
        sleepRandomTime()

        return self.is_in_lorentz_mode
    
    def resetToSafeState(self):
        sleepRandomTime()
        
        # wait for other actions to finish
        while (self.currently_setting_lorentz_mode or 
               self.currently_setting_measurement_variable is not None):
            time.sleep(0.01)
        
        self.is_in_safe_state = True

dummy_camera_name = "DummyCamera for testing"
class DummyCamera(pylo.CameraInterface):
    def __init__(self, controller):
        super().__init__(controller)
        self.microscope = controller.microscope
        self.img_count = 0
        self.is_in_safe_state = False
        self.currently_recording_image = False
    
    def resetToSafeState(self):
        sleepRandomTime()
        
        self.is_in_safe_state = True
    
    def recordImage(self, *args, **kwargs):
        self.currently_recording_image = True
        # self.is_in_safe_state = False
        size = len(self.microscope.supported_measurement_variables) + 1
        # create grayscale image
        image_data = np.zeros((size, max(2, size)), dtype=np.uint8)

        # save current image count first row in the first two pixels in the 
        # image
        image_data[0][0] = math.floor(self.img_count / 255)
        image_data[0][1] = self.img_count % 255

        # save current focus second row in the image, normed by min and max 
        # value
        f_var = self.microscope.getMeasurementVariableById("focus")
        image_data[1][0] = convertMeasurementVariableToImageSave(
                                f_var, self.microscope.focus)

        # save the magnetic field
        m_var = self.microscope.getMeasurementVariableById("lens-current")
        image_data[2][0] = convertMeasurementVariableToImageSave(
                                m_var, self.microscope.magnetic_field)

        # save the magnetic field
        t_var = self.microscope.getMeasurementVariableById("x-tilt")
        image_data[3][0] = convertMeasurementVariableToImageSave(
                                t_var, self.microscope.x_tilt)
        
        respond_time = sleepRandomTime()

        tags = {
            "exposure-time": respond_time,
            "image-count": self.img_count,
            "camera": dummy_camera_name
        }

        self.img_count += 1

        self.currently_recording_image = False

        return pylo.Image(image_data, tags)

def remove_dirs(directories=None):
    """Remove all given directories recursively with files inside."""
    if not isinstance(directories, (list, tuple)):
        directories = glob.glob(
            os.path.join(os.path.dirname(__file__), "tmp-test-measurement-*")
        )
    
    for directory in directories:
        if os.path.exists(directory):
            for f in os.listdir(directory):
                path = os.path.join(directory, f)
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    remove_dirs((path), )
        
            os.removedirs(directory)

class PerformedMeasurement:
    """This class performs one measurement and saves some specific values which
    are tested later.

    This is used as "caching" for the test. The measurement will be created 
    only once. This saves a lot of time.

    If the caching should not be enabled, so one measurement is performed for 
    each test, set the variable cache=False
    """

    def __init__(self, num=2, before_start=None, auto_start=True, 
                 collect_file_m_times=True):
        """Create and perform a measurement.

        Parameters
        ----------
        num : int or list of dicts, optional
            - 0: Measure 2 images: x-tilt -10deg and 10deg
            - 1: Measure 12 images: focus 0 and 5, field 0, 1 and 2 and x-tilt
                 -10deg and 10dev
            - 2: Measure 18 images: focus 0 and 5, field 0, 1, and 2 and x-tilt
                 -10deg, 0deg and 10deg
            - the list of steps
        before_start : callable, optional
            A callback that is executed before the measurement is started
        auto_start : bool, optional
            Whether to start the measurement automatically, default: True
        collect_file_m_times : bool, optional
            Whether to collect the file modification times on all images that 
            are *EXPTECTED TO BE CREATED*, default: True
        """
        self.root = os.path.join(
            os.path.dirname(__file__), 
            "tmp-test-measurement-{}".format(random.randint(0, 9999999))
        )

        remove_dirs((self.root, ))
        if not os.path.exists(self.root):
            os.mkdir(self.root, 0o760)

        self.controller = DummyController()
        self.measurement_steps = []

        if isinstance(num, (list, tuple, pylo.MeasurementSteps)):
            self.measurement_steps = num
        else:
            if num == 2:
                foci = (0, 5)
                fields = (0, 1, 2)
                tilts = (-10, 0, 10)
            elif num == 1:
                foci = (0, 5)
                fields = (0, 1, 2)
                tilts = (-10, 10)
            else:
                foci = (0, )
                fields = (0,)
                tilts = (-10, 10)

            for f in foci:
                for m in fields:
                    for t in tilts:
                        self.measurement_steps.append({
                            "focus": f, 
                            "lens-current": m, 
                            "x-tilt": t
                        })

        pylo.Measurement.defineConfigurationOptions(self.controller.configuration)
        self.controller.configuration.setValue(
            "measurement", "microscope-to-safe-state-after-measurement", True
        )
        self.controller.configuration.setValue(
            "measurement", "camera-to-safe-state-after-measurement", True
        )
        self.controller.configuration.setValue(
            "measurement", "log-save-path", os.path.join(self.root, "measurement.log")
        )
        self.controller.configuration.setValue(
            "measurement", "save-directory", self.root
        )
        self.controller.configuration.setValue(
            "measurement", "save-file-format", "{counter}-dummy-measurement.tif"
        )
        self.measurement = pylo.Measurement(self.controller, self.measurement_steps)
        # self.measurement.save_dir = self.root
        # self.measurement.name_format = "{counter}-dummy-measurement.tif"

        self.measurement.tags["test key"] = "Test Value"
        self.measurement.tags["test key 2"] = 2
        self.measurement.tags["test key 3"] = False

        # add counter for testing
        self.name_test_format = ["{counter}"]
        # add all measurement variables
        for var in self.controller.microscope.supported_measurement_variables:
            # self.name_test_format.append("{{varname[{v}]}}".format(v=var.unique_id))
            self.name_test_format.append("{{step[{v}]}}".format(v=var.unique_id))
        # add all tags
        for key in self.measurement.tags:
            self.name_test_format.append("{tags[" + key + "]}")
        # add time
        self.name_test_format.append("{time:%Y%m%d%H%M,%S}")
        # convert to string
        self.name_test_format = ";".join(self.name_test_format)

        # prepare event timers
        self.microscope_ready_time = []
        self.before_approach_time = []
        self.before_record_time = []
        self.after_record_time = []
        self.measurement_ready_time = []

        # formatted names
        self.formatted_names = []
        # all the steps that are not visited
        self.unvisited_steps = self.measurement_steps.copy()

        # clear events
        pylo.microscope_ready.clear()
        pylo.before_record.clear()
        pylo.after_record.clear()
        pylo.measurement_ready.clear()

        # clear events
        pylo.microscope_ready.clear()
        pylo.before_record.clear()
        pylo.after_record.clear()
        pylo.measurement_ready.clear()

        # register events
        pylo.microscope_ready["performed_measurement_handler"] = self.microscope_ready_handler
        pylo.before_approach["performed_measurement_handler"] = self.before_approach_handler
        pylo.before_record["performed_measurement_handler"] = self.before_record_handler
        pylo.after_record["performed_measurement_handler"] = self.after_record_handler
        pylo.measurement_ready["performed_measurement_handler"] = self.measurement_ready_handler

        pylo.microscope_ready["performed_measurement_check_lorentz"] = self.check_if_microscope_in_lorentz_mode
        pylo.after_record["performed_measurement_prepare_names"] = self.prepare_names_handler
        pylo.after_record["performed_measurement_step_visited"] = self.every_step_visited_handler

        if callable(before_start):
            before_start(self)
        
        self.file_m_times = []
        self.start_time = time.time()
        
        if auto_start:
            # start in separate thread for testing, this will probaobly be in a 
            # separate thread later too, so include it for testing
            thread = pylo.ExceptionThread(target=self.measurement.start())
            thread.start()
            thread.join()

            for e in thread.exceptions:
                raise e

            self.measurement.waitForAllImageSavings()

            if collect_file_m_times:
                self.file_m_times = list(map(lambda x: os.path.getmtime(x), 
                                            self.get_image_paths()))
            else:
                self.file_m_times = []
    
    def get_image_paths(self, counter=None):
        """A generator that returns the file name until the counter, if the 
        counter is not given the number of steps will be used for the counter.

        Parameters
        ----------
        counter : int, optional
            The end number of the file name to return (not inculding the 
            counter)
        
        Yields
        ------
        str
            The image paths
        """

        if not isinstance(counter, int):
            counter = len(self.measurement_steps)
        
        for i in range(counter):
            yield os.path.join(
                self.root, 
                self.measurement.name_format.format(counter=i)
            )
    
    def microscope_ready_handler(self, *args):
        self.microscope_ready_time.append(time.time())
    
    def before_approach_handler(self, *args):
        self.before_approach_time.append(time.time())
    
    def before_record_handler(self, *args):
        self.before_record_time.append(time.time())
    
    def after_record_handler(self, *args):
        self.after_record_time.append(time.time())
    
    def measurement_ready_handler(self, *args):
        self.measurement_ready_time.append(time.time())
    
    def prepare_names_handler(self, *args):
        self.formatted_names.append(self.measurement.formatName(self.name_test_format))
    
    def every_step_visited_handler(self, *args):
        step = self.measurement.steps[self.measurement.step_index]

        try:
            self.unvisited_steps.remove(step)
        except ValueError:
            pass
    
    def check_if_microscope_in_lorentz_mode(self, *args):
        assert self.controller.microscope.is_in_lorentz_mode
    
performed_measurement_obj = None
performed_measurement_substeps = None

@pytest.fixture
def performed_measurement(performed_measurement_cache=True):
    """Get the performed measurement.

    If cache is False, always a new measurement will be created

    Returns
    -------
    PerformedMeasurement
        The measurement
    """

    global performed_measurement_obj

    if (not performed_measurement_cache or 
        not isinstance(performed_measurement_obj, PerformedMeasurement)):
        # recreate if not cache
        performed_measurement_obj = PerformedMeasurement()
    
    return performed_measurement_obj

class DummyException(Exception):
    pass

class TestMeasurement:
    @classmethod
    def teardown_class(cls):
        remove_dirs()
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_all_steps_produced_images(self, performed_measurement):
        """Test if there are all the image files that are expected."""

        for f in performed_measurement.get_image_paths():
            assert os.path.exists(f)
            assert os.path.isfile(f)
            assert os.path.getmtime(f) >= performed_measurement.start_time
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_all_steps_content_of_images(self, performed_measurement):
        """Test if the content of the image is correct, this tests whether the
        image is readable and saved correctly (which is redundant with the 
        image test) plus whether the values are actually set in the microscope
        because the microscope values are saved in the image."""

        f_var = performed_measurement.controller.microscope.getMeasurementVariableById("focus")
        f_prec = (f_var.max_value - f_var.min_value) / 255
        m_var = performed_measurement.controller.microscope.getMeasurementVariableById("lens-current")
        m_prec = (m_var.max_value - m_var.min_value) / 255
        t_var = performed_measurement.controller.microscope.getMeasurementVariableById("x-tilt")
        t_prec = (t_var.max_value - t_var.min_value) / 255

        for i, f in enumerate(performed_measurement.get_image_paths()):
            load_img = PILImage.open(f)
            image_data = np.array(load_img)

            counter = image_data[0][0] * 255 + image_data[0][1]
            focus = convertImageSaveToMeasurementVariable(
                        f_var, image_data[1][0])
            magnetic_field = convertImageSaveToMeasurementVariable(
                        m_var, image_data[2][0])
            x_tilt = convertImageSaveToMeasurementVariable(
                        t_var, image_data[3][0])
            
            assert counter == i
            assert math.isclose(focus, 
                                performed_measurement.measurement_steps[i]["focus"], 
                                abs_tol=f_prec)
            assert math.isclose(magnetic_field, 
                                performed_measurement.measurement_steps[i]["lens-current"], 
                                abs_tol=m_prec)
            assert math.isclose(x_tilt, 
                                performed_measurement.measurement_steps[i]["x-tilt"], 
                                abs_tol=t_prec)
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_all_events_are_called(self, performed_measurement):
        """Test if all the expected events are fired."""
        assert len(performed_measurement.microscope_ready_time) > 0
        assert len(performed_measurement.before_record_time) > 0
        assert len(performed_measurement.after_record_time) > 0
        assert len(performed_measurement.measurement_ready_time) > 0
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_microscope_ready_event_time(self, performed_measurement):
        """Test if the microscope_ready event is fired after the start but 
        before all other events and before any image is created."""

        # microscope ready is only called once
        assert len(performed_measurement.microscope_ready_time) == 1

        assert performed_measurement.start_time < performed_measurement.microscope_ready_time[0]
        # before record is triggered right after the microscope ready with not
        # much code inbetween, therefore this is probably always the same time
        assert (performed_measurement.microscope_ready_time[0] <=
                min(performed_measurement.before_record_time))
        assert (performed_measurement.microscope_ready_time[0] < 
                min(performed_measurement.after_record_time))
        assert (performed_measurement.microscope_ready_time[0] < 
                performed_measurement.measurement_ready_time[0])

        # microscope has to be ready before any image is recorded
        assert (performed_measurement.microscope_ready_time[0] < 
                min(performed_measurement.file_m_times))
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_before_record_event_time(self, performed_measurement):
        """Test if the all before_record event are fired after the start but 
        before after_record and measurement_ready events and before the 
        image is created."""

        # there is a before record for every measurement step
        assert (len(performed_measurement.before_record_time) == 
                len(performed_measurement.measurement_steps))

        assert (performed_measurement.start_time < 
                min(performed_measurement.before_record_time))
        # before record is triggered right after the microscope ready with not
        # much code inbetween, therefore this is probably always the same time
        assert (performed_measurement.microscope_ready_time[0] <= 
                min(performed_measurement.before_record_time))
        # all before_record times must be before the after_record times
        assert (np.all(np.array(performed_measurement.before_record_time) < 
                np.array(performed_measurement.after_record_time)))
        assert (max(performed_measurement.before_record_time) < 
                performed_measurement.measurement_ready_time[0])

        # before_record is fired before the corresponding image is created
        assert np.all(np.array(performed_measurement.before_record_time) < 
                      np.array(performed_measurement.file_m_times))
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_after_record_event_time(self, performed_measurement):
        """Test if the all after_record event are fired after each record 
        and before the measurement_ready events and after the image is created 
        (but before it is saved)."""

        # there is a before record for every measurement step
        assert (len(performed_measurement.after_record_time) == 
                len(performed_measurement.measurement_steps))

        assert (performed_measurement.start_time < 
                min(performed_measurement.after_record_time))
        assert (performed_measurement.microscope_ready_time[0] < 
                min(performed_measurement.after_record_time))
        # all before_record times must be before the after_record times
        assert np.all(np.array(performed_measurement.before_record_time) < 
                      np.array(performed_measurement.after_record_time))
        assert (max(performed_measurement.after_record_time) <= 
                performed_measurement.measurement_ready_time[0])
                
        for after_time, m_time in zip(performed_measurement.after_record_time, 
                                      performed_measurement.file_m_times):
            assert after_time <= m_time or math.isclose(after_time, m_time, 
                                                        rel_tol=0, abs_tol=1e-6)
                           
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")                       
    def test_measurement_ready_event_time(self, performed_measurement):
        """Test if the measurement_ready event is fired after all other events
        and after all images are created."""

        # microscope ready is only called once
        assert (len(performed_measurement.measurement_ready_time) == 1)

        assert (performed_measurement.start_time < 
                performed_measurement.measurement_ready_time[0])
        # before record is triggered right after the microscope ready with not
        # much code inbetween, therefore this is probably always the same time
        assert (performed_measurement.microscope_ready_time[0] < 
                performed_measurement.measurement_ready_time[0])
        assert (min(performed_measurement.before_record_time) < 
                performed_measurement.measurement_ready_time[0])
        assert (min(performed_measurement.after_record_time) <= 
                performed_measurement.measurement_ready_time[0])

        # microscope has to be ready before any image is recorded
        assert (max(performed_measurement.file_m_times) <=
                performed_measurement.measurement_ready_time[0])
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_format_name_on_each_step(self, performed_measurement):
        """Test if the nameFormat() function uses the correct values on each
        step."""

        measurement_variable_ids = [x.unique_id 
            for x in performed_measurement.controller.microscope.supported_measurement_variables]
        
        for i, name in enumerate(performed_measurement.formatted_names):
            name = name.split(";")

            # check the counter
            s = 0
            e = 1
            assert "{}".format(name[s]) == str(i)

            # check the values of all the measurement variables saved in the 
            # string, do not rely on the order
            s = e
            e += len(measurement_variable_ids)
            check_values = name[s:e]
            for variable_id in measurement_variable_ids:
                expected_value = performed_measurement.measurement_steps[i][variable_id]
                assert "{}".format(expected_value) in check_values
            
            # check the tags of the measurement
            s = e
            e += len(performed_measurement.measurement.tags)
            check_tags = name[s:e]
            for key in performed_measurement.measurement.tags:
                assert ("{}".format(performed_measurement.measurement.tags[key]) 
                        in check_tags)
            
            # image tags are not supported anymore
            # # check some image tags
            # s = e
            # e += 2
            # check_imgtags = name[s:e]
            # # check the image counter, it should be equal to the step counter
            # assert "{}".format(i) in check_imgtags
            # # check the camera name
            # assert "{}".format(dummy_camera_name) in check_imgtags

            # test time
            s = e
            e += 1
            check_time = name[s].split(",")
            expected_time = datetime.datetime.fromtimestamp(
                performed_measurement.after_record_time[i])
            assert check_time[0] == expected_time.strftime("%Y%m%d%H%M")
            # check if time is one second close, the after_record is fired 
            # before the save so it might not be exactly the same
            assert math.isclose(int(check_time[1]), int(expected_time.second), abs_tol=1)

            # check if all parts are checked
            assert e == len(name)
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_missing_keys_in_format_name(self, performed_measurement):
        """Test if missing keys/wrong placeholders are just ignored in the 
        formatName() function"""

        assert performed_measurement.measurement.formatName("{nonexitingplaceholder}") == ""
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_all_steps_visited(self, performed_measurement):
        """Test if all steps that were defined are visited."""

        assert len(performed_measurement.unvisited_steps) == 0
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_log_created(self, performed_measurement):
        """Test if there is a log created."""
        assert os.path.exists(performed_measurement.measurement._measurement_log_path)
        assert os.path.isfile(performed_measurement.measurement._measurement_log_path)
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_log_row_count_is_correct(self, performed_measurement):
        """Test if there is a log has the correct number of rows."""
        
        with open(performed_measurement.measurement._measurement_log_path) as f:
            line_num = sum([1 if line != "" else 0 for line in f])

            # for each step one log before and one after, then plus one for the 
            # header
            assert (line_num == 
                    2 * len(performed_measurement.measurement_steps) + 1)
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_log_is_correct(self, performed_measurement):
        """Test if the log is correct."""

        # for row in performed_measurement.measurement._debug_log:
        #     print(row)
        # assert False
        
        with open(performed_measurement.measurement._measurement_log_path) as f:
            reader = csv.reader(f)
            
            column_order = {}
            for i, row in enumerate(reader):
                if i == 0:
                    # header
                    for v in performed_measurement.controller.microscope.supported_measurement_variables:
                        found = False
                        for j, cell in enumerate(row):
                            if v.name in cell:
                                found = True
                                index = cell.index(v.name)

                                column_order[j] = v.unique_id

                                if v.unit is not None:
                                    # unit has to be after the variable name
                                    assert v.unit in cell[index:]
                                
                                if v.has_calibration:
                                    # calibrated name is after the uncalibrated
                                    following_cells = "".join(row[j:])
                                    assert v.calibrated_name in following_cells
                                    index = following_cells.index(v.calibrated_name)

                                    if v.calibrated_unit is not None:
                                        # unit has to be after the variable name
                                        assert v.calibrated_unit in following_cells[index:]
                                    
                                    # column j + 1 contains the calibrated value
                                    # del column_order[j]
                                    # column_order[j + 1] = v.unique_id

                                    break
                        
                        assert found
                else:
                    if i % 2 == 1:
                        assert "Targetting value" in row[0]
                    else:
                        assert "Recording image" in row[0]
                    
                    # ignore the header, for each step there are two entries
                    step = performed_measurement.measurement_steps[(i - 1) // 2]

                    for j, id_ in column_order.items():
                        v = performed_measurement.controller.microscope.getMeasurementVariableById(id_)

                        # check the value (this is the uncalibrated value if 
                        # there is a calibration value)
                        if isinstance(v.format, pylo.Datatype):
                            # check if the value is correct
                            assert (float(v.format.parse(row[j])) == 
                                    float(step[id_]))
                            # check if the stored format is correct
                            assert v.format.format(step[id_]) == row[j]
                        else:
                            assert float(row[j]) == float(step[id_])

                        if v.has_calibration:
                            # check the calibrated value
                            j += 1
                            val = v.convertToCalibrated(step[id_])

                            if isinstance(v.calibrated_format, pylo.Datatype):
                                assert (float(v.calibrated_format.parse(row[j])) == 
                                        float(val))
                                # check if the stored format is correct
                                assert (v.calibrated_format.format(val) == 
                                        row[j])
                            else:
                                assert float(row[j]) == float(val)
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_microscope_in_safe_state(self, performed_measurement):
        """Test if the microscope is in the safe state after the measurmenet
        has finished."""
        assert performed_measurement.controller.microscope.is_in_safe_state
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_camera_in_safe_state(self, performed_measurement):
        """Test if the camera is in the safe state after the measurmenet
        has finished."""
        assert performed_measurement.controller.camera.is_in_safe_state
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def check_measurement_is_stopped(self, perf_measurement, check_files=False):
        """Check if the given measurement is stopped at any time, check if 
        there are no files created if `check_files` is True."""

        assert not perf_measurement.measurement.running
        assert perf_measurement.controller.microscope.is_in_safe_state
        assert perf_measurement.controller.camera.is_in_safe_state

        if check_files:
            for f in glob.glob(os.path.join(perf_measurement.root, "*.tif")):
                assert os.path.getmtime(f) < perf_measurement.start_time
    
    def test_stop_stops_execution_in_microscope_ready(self):
        """Test if firing the stop event in the microscope_ready event callback 
        cancels the execution of the measurement."""
        performed_measurement = PerformedMeasurement(0, 
            lambda m: pylo.microscope_ready.__setitem__("test_measurement_stop", 
                                                        m.measurement.stop),
            collect_file_m_times=False
        )

        self.check_measurement_is_stopped(performed_measurement)

        # check that the following events are executed
        assert len(performed_measurement.microscope_ready_time) == 1
        # check that the following events are not executed
        assert len(performed_measurement.before_record_time) == 0
        assert len(performed_measurement.after_record_time) == 0
        assert len(performed_measurement.measurement_ready_time) == 0

        # check if no image is recorded
        file_found = False
        for f in os.listdir(performed_measurement.root):
            if f != "." and f != ".." and f != "measurement.log":
                file_found = True
                break
        assert not file_found
    
    def test_stop_stops_execution_in_before_record(self):
        """Test if firing the stop event in the before_record event callback 
        cancels the execution of the measurement."""
        performed_measurement = PerformedMeasurement(0, 
            lambda m: pylo.before_record.__setitem__("test_measurement_stop", 
                                                     m.measurement.stop),
            collect_file_m_times=False
        )

        self.check_measurement_is_stopped(performed_measurement)

        # check that the following events are executed
        assert len(performed_measurement.microscope_ready_time) == 1
        assert len(performed_measurement.before_record_time) == 1
        # check that the following events are not executed
        assert len(performed_measurement.after_record_time) == 0
        assert len(performed_measurement.measurement_ready_time) == 0

        # check if no image is recorded
        file_found = False
        for f in os.listdir(performed_measurement.root):
            if f != "." and f != ".." and f != "measurement.log":
                file_found = True
                break
        assert not file_found
    
    def test_stop_stops_execution_in_after_record(self):
        """Test if firing the stop event in the after_record event callback 
        cancels the execution of the measurement."""
        performed_measurement = PerformedMeasurement(0, 
            lambda m: pylo.after_record.__setitem__("test_measurement_stop", 
                                                    m.measurement.stop),
            collect_file_m_times=False
        )

        self.check_measurement_is_stopped(performed_measurement)

        # check that the following events are executed
        assert len(performed_measurement.microscope_ready_time) == 1
        assert len(performed_measurement.before_record_time) == 1
        assert len(performed_measurement.after_record_time) == 1
        # check that the following events are not executed
        assert len(performed_measurement.measurement_ready_time) == 0

        # check if no image is recorded, after_record is fired before saving
        # starts!
        file_found = False
        for f in os.listdir(performed_measurement.root):
            if f != "." and f != ".." and f != "measurement.log":
                file_found = True
                break
        assert not file_found
    
    def stop_measurement_after(self, perf_measurement, stop_time):
        """Stop the measurement after the amout of time."""
        time.sleep(stop_time)
        perf_measurement.measurement.stop()

    @pytest.mark.slow()
    def test_stop_stops_while_setting_lorentz_mode(self):
        """Test whether a stop call stops the microscope while it is setting
        the lorentz mode."""
        # make the sleep time (=time the microscope and camera take to perform
        # their action) big enough so the stop call is somewhere inbetween
        operation_time = 2
        setSleepTime(operation_time)

        performed_measurement = PerformedMeasurement(0, auto_start=False)
        thread = pylo.ExceptionThread(target=self.stop_measurement_after, 
                                  args=(performed_measurement, 
                                        operation_time / 2))
        thread.start()

        # start the measurement in this thread
        performed_measurement.measurement.start()
        
        # make sure only the lorentz mode is set (this is not breakable) and
        # then the function exits and give some buffer (10%)
        assert time.time() <= (performed_measurement.start_time + 
                               operation_time * 1.1)

        # wait until the stop thread is done
        thread.join()

        self.check_measurement_is_stopped(performed_measurement)

        # check that the following events are not executed
        assert len(performed_measurement.microscope_ready_time) == 0
        assert len(performed_measurement.before_record_time) == 0
        assert len(performed_measurement.after_record_time) == 0
        assert len(performed_measurement.measurement_ready_time) == 0

        # wait for all file handles to close
        performed_measurement.measurement.waitForAllImageSavings()
        # reset the sleep time to be random again
        setSleepTime("random")

    @pytest.mark.slow()
    def test_stop_stops_while_setting_measurement_variable(self):
        """Test whether a stop call stops the microscope while it is setting
        a measurement variable."""
        # make the sleep time (=time the microscope and camera take to perform
        # their action) big enough so the stop call is somewhere inbetween
        operation_time = 2
        setSleepTime(operation_time)

        performed_measurement = PerformedMeasurement(0, auto_start=False)
        thread = pylo.ExceptionThread(target=self.stop_measurement_after, 
                                  args=(performed_measurement, 
                                        operation_time * 1.5))
        thread.start()

        # start the measurement in this thread
        performed_measurement.measurement.start()
        
        # make sure only the lorentz mode is set (one operation time) and the 
        # measurement variable is set (another operation time) and give some 
        # buffer (10%)
        assert time.time() <= (performed_measurement.start_time + 
                               operation_time * 2 * 1.1)

        # wait until the stop thread is done
        thread.join()

        self.check_measurement_is_stopped(performed_measurement)

        # check that the following events are executed
        assert len(performed_measurement.microscope_ready_time) > 0
        assert len(performed_measurement.before_approach_time) > 0
        # check that the following events are not executed
        assert len(performed_measurement.before_record_time) == 0
        assert len(performed_measurement.after_record_time) == 0
        assert len(performed_measurement.measurement_ready_time) == 0

        # wait for all file handles to close
        performed_measurement.measurement.waitForAllImageSavings()
        # reset the sleep time to be random again
        setSleepTime("random")
    
    def after_stop_handler(self, *args):
        """The event handler for testing the after_stop event."""
        self.after_stop_times.append(time.time())
    
    @pytest.mark.parametrize("microscope_to_safe,camera_to_safe", [
        (True, False),
        (False, False),
        (False, True)
    ])
    def test_not_in_safe_state(self, microscope_to_safe, camera_to_safe):
        """Test if the micorsocpe and/or camera should not be in the safe 
        state after the measurement, they aren't.
        """

        setSleepTime(0.1)
        performed_measurement = PerformedMeasurement(0, auto_start=False)
        
        performed_measurement.measurement.microscope_safe_after = microscope_to_safe
        performed_measurement.measurement.camera_safe_after = camera_to_safe

        performed_measurement.measurement.start()

        assert (performed_measurement.controller.microscope.is_in_safe_state == 
                microscope_to_safe)
        assert (performed_measurement.controller.camera.is_in_safe_state == 
                camera_to_safe)

        # wait for all file handles to close
        performed_measurement.measurement.waitForAllImageSavings()
        setSleepTime("random")
    
    @pytest.mark.slow()
    @pytest.mark.parametrize("relaxation_time", [
        0, 2
    ])
    def test_relaxation_time(self, relaxation_time):
        """Test if the relaxation time works correctly."""

        setSleepTime(0)
        performed_measurement = PerformedMeasurement(0, auto_start=False)
        performed_measurement.measurement.relaxation_time = relaxation_time

        start_time = time.time()
        performed_measurement.measurement.start()
        performed_measurement.measurement.waitForAllImageSavings()
        end_time = time.time()

        assert ((start_time + relaxation_time >= 
                performed_measurement.microscope_ready_time[0]) or
                math.isclose(start_time + relaxation_time, 
                             performed_measurement.microscope_ready_time[0],
                             abs_tol=0.1))
        assert (end_time - start_time > relaxation_time or
                math.isclose(end_time - start_time, relaxation_time, abs_tol=0.1))

        # wait for all file handles to close
        performed_measurement.measurement.waitForAllImageSavings()
        setSleepTime("random")
    
    def check_events(self, stop_callable):
        """Perform the test for the events, the code is nearly the same so use
        it for both tests."""

        # make the sleep time (=time the microscope and camera take to perform
        # their action) big enough so the stop call is somewhere inbetween
        operation_time = 0.5
        setSleepTime(operation_time)

        self.after_stop_times = []
        pylo.after_stop.clear()
        pylo.after_stop["test_measurement_stop"] = self.after_stop_handler

        performed_measurement = PerformedMeasurement(0, auto_start=False)

        # start the measurement another thread
        thread = pylo.ExceptionThread(target=performed_measurement.measurement.start)
        thread.start()

        # stop the measurement
        stop_callable(performed_measurement, operation_time)

        # event is triggered after stop, if blocked function is called, the 
        # event may be called a second time
        assert len(self.after_stop_times) >= 1
        # event is triggered immediately after the stop call
        assert math.isclose(self.after_stop_times[0], time.time(), rel_tol=0,
                            abs_tol=0.1)

        # wait until the thread is done
        thread.join()

        # check if the measurement is acutally stopped
        self.check_measurement_is_stopped(performed_measurement)

        # wait for all file handles to close
        performed_measurement.measurement.waitForAllImageSavings()
        # reset the sleep time to be random again
        setSleepTime("random")
        pylo.after_stop.clear()
    
    def test_after_stop_event_is_triggered(self):
        """Test whether a stop call triggers the after_stop event."""
        self.check_events(lambda p, t: self.stop_measurement_after(p, t))

    def test_emergency_event_stops_measurement(self):
        """Test if firing the emergency event stops the measurement."""
        pylo.emergency.clear()
        self.check_events(lambda p, t: pylo.emergency())
        pylo.emergency.clear()
    
    def throw_exception(self, *args):
        raise DummyException("This is an exception to test whether exceptions " + 
                             "are handled correctly.")

    def test_exception_in_microscope_ready_stops_measurement(self):
        """Test if an exception in the microscope_ready event stops the 
        measurement."""
        with pytest.raises(DummyException):
            performed_measurement = PerformedMeasurement(0, 
                lambda m: pylo.microscope_ready.__setitem__("test_measurement_exception", 
                                                            self.throw_exception)
            )

            self.check_measurement_is_stopped(performed_measurement)

            # check that the following events are executed
            assert len(performed_measurement.microscope_ready_time) == 1
            # check that the following events are not executed
            assert len(performed_measurement.before_record_time) == 0
            assert len(performed_measurement.after_record_time) == 0
            assert len(performed_measurement.measurement_ready_time) == 0

    def test_exception_in_before_record_stops_measurement(self):
        """Test if an exception in the before_record event stops the 
        measurement."""
        with pytest.raises(DummyException):
            performed_measurement = PerformedMeasurement(0, 
                lambda m: pylo.before_record.__setitem__("test_measurement_exception", 
                                                         self.throw_exception)
            )

            self.check_measurement_is_stopped(performed_measurement)

            # check that the following events are executed
            assert len(performed_measurement.microscope_ready_time) == 1
            assert len(performed_measurement.before_record_time) == 1
            # check that the following events are not executed
            assert len(performed_measurement.after_record_time) == 0
            assert len(performed_measurement.measurement_ready_time) == 0

    def test_exception_in_after_record_stops_measurement(self):
        """Test if an exception in the after_record event stops the 
        measurement."""
        with pytest.raises(DummyException):
            performed_measurement = PerformedMeasurement(0, 
                lambda m: pylo.after_record.__setitem__("test_measurement_exception", 
                                                        self.throw_exception)
            )

            self.check_measurement_is_stopped(performed_measurement)

            # check that the following events are executed
            assert len(performed_measurement.microscope_ready_time) == 1
            assert len(performed_measurement.before_record_time) == 1
            assert len(performed_measurement.after_record_time) == 1
            # check that the following events are not executed
            assert len(performed_measurement.measurement_ready_time) == 0

    def test_exception_stops_measurement(self):
        """Test if an exception at a random time stops the measurement."""
        with pytest.raises(DummyException):
            self.check_events(self.throw_exception)
    
    def prepare_substeps(self, cache=True):
        global performed_measurement_substeps
        
        steps = []
        for field in (0, 2):
            for tilt in (-10, 10):
                steps.append({
                    "focus": 0,
                    "lens-current": field,
                    "x-tilt": tilt
                })
        
        step_count = len(steps)
        substep_count = 10

        if performed_measurement_substeps is None or not cache:
            performed_measurement_substeps = PerformedMeasurement(num=steps, 
                auto_start=False, collect_file_m_times=False)

            setSleepTime(0.01)

            performed_measurement_substeps.measurement.substep_count = substep_count

            thread = pylo.ExceptionThread(target=performed_measurement_substeps.measurement.start())
            thread.start()
            thread.join()

            for e in thread.exceptions:
                raise e
            
            setSleepTime("random")

        return performed_measurement_substeps, step_count, substep_count, steps
    
    @pytest.mark.slow()
    def test_substeps_steps(self):
        """Test if every single step is reached in the correct order."""
        perf_m, step_number, substep_count, steps = self.prepare_substeps()
        
        last_time = None
        for step in steps:
            found_steps = []

            for log_step, log_time in perf_m.controller.microscope.measurement_variable_set_log:
                matches = True
                for id_ in step:
                    if not math.isclose(step[id_], log_step[id_]):
                        matches = False
                        break
                
                if matches:
                    found_steps.append((log_step, log_time))
            
            assert len(log_step) > 0

            found_steps.sort(key=lambda s: s[1])
            
            if last_time is None:
                last_time = found_steps[0][1]
            else:
                found = False
                for log_step, log_time in found_steps:
                    if log_time > last_time:
                        found = True
                        last_time = log_time
                        break
                
                assert found
    
    @pytest.mark.slow()
    def test_substeps_steps_2(self):
        """Test if the substeps work."""
        perf_m, step_number, substep_count, steps = self.prepare_substeps()

        # remove setting of zero to all values
        log = copy.deepcopy(perf_m.controller.microscope.measurement_variable_set_log)
        offset = None
        for offset, (step, time) in enumerate(log):
            only_zero = True
            for id_ in step:
                if step[id_] != 0:
                    only_zero = False
                    break
            
            if not only_zero:
                break
        
        if offset > 0:
            log = log[offset:]
        
        log.sort(key=lambda x: x[1])
        
        d = {"focus": 0,
             "lens-current": (2 - 0) / 10,
             "x-tilt": (10 + 10) / 10}

        prev_step = None
        for step, time in log:
            if prev_step is not None:
                for k in step:
                    # either no change in the variable or a change that is 
                    # equal to a substep stepwidth
                    ds = abs(step[k] - prev_step[k])

                    assert math.isclose(ds, 0) or math.isclose(ds, d[k])

            prev_step = copy.deepcopy(step)
    
    @pytest.mark.slow()
    def test_substeps_time(self):
        """Test if the substeps work."""
        # the time setting a measurement variable takes (thread is sleeping
        # this time to fake i/o operations)
        sleep_time = 0.01
        start_time = time.time()

        perf_m, step_number, substep_count, steps = self.prepare_substeps(cache=False)

        end_time = time.time()
        total_duration = (step_number * substep_count * sleep_time + 
                          perf_m.measurement.relaxation_time * step_number + 
                          # set to lorentz mode
                          sleep_time)
        
        print("Expected duration:", total_duration, 
              "Actual duration:", end_time - start_time)

        assert math.isclose(end_time - start_time - total_duration, 0, abs_tol=0.2)

        lt = None
        for step, t in perf_m.controller.microscope.measurement_variable_set_log:
            assert ((start_time <= t and t < end_time) or 
                    (start_time < t and t <= end_time))
                    
            if lt is not None:
                assert t >= lt
            lt = t

if __name__ == "__main__":
    pass
