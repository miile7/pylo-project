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
import pylo.cameras
import pylo.microscopes

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

class DummyMicroscope(pylo.microscopes.MicroscopeInterface):
    def __init__(self, controller):
        super().__init__(controller)

        self.supported_measurement_variables = [
            pylo.MeasurementVariable("focus", "Focus", 0, 10, "mA"),
            pylo.MeasurementVariable("lense-current", "OM Current", 0, 3, 
                                     format=pylo.microscopes.pyjem_microscope.hex_int,
                                     calibration=2, calibrated_unit="T",
                                     calibrated_name="Magnetic Field"),
            pylo.MeasurementVariable("x-tilt", "Tilt (x direction)", -35, 35, "deg")
        ]

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

        self.is_in_safe_state = False
        sleepRandomTime()

        # simulate small variance in real value in first or second digit after 
        # decimal separator
        # value += (random.random() - 0.5) / 10

        if id_ == "focus":
            self.focus = value
        elif id_ == "lense-current":
            self.magnetic_field = value
        elif id_ == "x-tilt":
            self.x_tilt = value
        else:
            raise KeyError("The measurement variable {} does not exist.".format(id_))
            
        self.currently_setting_measurement_variable = None
        self.currently_setting_lorentz_mode = False

    def getMeasurementVariableValue(self, id_):
        sleepRandomTime()

        if id_ == "focus":
            return self.focus
        elif id_ == "lense-current":
            return self.magnetic_field
        elif id_ == "x-tilt":
            return self.x_tilt
        else:
            raise KeyError("The measurement variable {} does not exist.".format(id_))
    
    def setInLorentzMode(self, lorentz_mode):
        self.currently_setting_lorentz_mode = True
        sleepRandomTime()

        if lorentz_mode:
            self.is_in_safe_state = False
        
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
class DummyCamera(pylo.cameras.CameraInterface):
    def __init__(self, controller):
        super().__init__(controller)
        self.microscope = controller.microscope
        self.img_count = 0
        self.is_in_safe_state = False
        self.currently_recording_image = False
    
    def resetToSafeState(self):
        sleepRandomTime()
        
        self.is_in_safe_state = True
    
    def recordImage(self):
        self.currently_recording_image = True
        self.is_in_safe_state = False
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
        m_var = self.microscope.getMeasurementVariableById("lense-current")
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

class DummyConfiguration(pylo.AbstractConfiguration):
    def __init__(self):
        super().__init__()
    
    def loadConfiguration(self):
        pass
    
    def saveConfiguration(self):
        pass

class DummyController(pylo.Controller):
    def __init__(self):
        self.microscope = DummyMicroscope(self)
        self.camera = DummyCamera(self)
        self.configuration = DummyConfiguration()
        self.view = DummyView()

class DummyView(pylo.AbstractView):
    def askFor(self, *args, **kwargs):
        print(args, kwargs)
        assert False
        return ["DEFAULT_ASK_FOR_ANSWER"] * len(args)
    
    def showError(self, error, how_to_fix):
        if isinstance(error, Exception):
            raise error
        else:
            raise Exception(error)
    
    def _updateRunning(self):
        pass

    def print(self, *inputs, sep=" ", end="\n", inset=""):
        print(*inputs, sep=sep, end=end)

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
        num : int, optional
            - 0: Measure 2 images: x-tilt -10deg and 10deg
            - 1: Measure 12 images: focus 0 and 5, field 0, 1 and 2 and x-tilt
                 -10deg and 10dev
            - 2: Measure 18 images: focus 0 and 5, field 0, 1, and 2 and x-tilt
                 -10deg, 0deg and 10deg
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
                        "lense-current": m, 
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
            self.name_test_format.append("{variables[" + var.unique_id + "]}")
        # add all tags
        for key in self.measurement.tags:
            self.name_test_format.append("{tags[" + key + "]}")
        # add some static/assumable image tags
        self.name_test_format.append("{imgtags[image-count]}")
        self.name_test_format.append("{imgtags[camera]}")
        # add time
        self.name_test_format.append("{time:%Y%m%d%H%M,%S}")
        # convert to string
        self.name_test_format = ";".join(self.name_test_format)

        # prepare event timers
        self.microscope_ready_time = []
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
        pylo.microscope_ready.append(self.microscope_ready_handler)
        pylo.before_record.append(self.before_record_handler)
        pylo.after_record.append(self.after_record_handler)
        pylo.measurement_ready.append(self.measurement_ready_handler)

        pylo.microscope_ready.append(self.check_if_microscope_in_lorentz_mode)
        pylo.after_record.append(self.prepare_names_handler)
        pylo.after_record.append(self.every_step_visited_handler)

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
    
    def microscope_ready_handler(self):
        self.microscope_ready_time.append(time.time())
    
    def before_record_handler(self):
        self.before_record_time.append(time.time())
    
    def after_record_handler(self):
        self.after_record_time.append(time.time())
    
    def measurement_ready_handler(self):
        self.measurement_ready_time.append(time.time())
    
    def prepare_names_handler(self):
        self.formatted_names.append(self.measurement.formatName(self.name_test_format))
    
    def every_step_visited_handler(self):
        step = self.measurement.steps[self.measurement._step_index]

        try:
            self.unvisited_steps.remove(step)
        except ValueError:
            pass
    
    def check_if_microscope_in_lorentz_mode(self):
        assert self.controller.microscope.is_in_lorentz_mode
    
performed_measurement_obj = None

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
        m_var = performed_measurement.controller.microscope.getMeasurementVariableById("lense-current")
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
                                performed_measurement.measurement_steps[i]["lense-current"], 
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
            
            # check some image tags
            s = e
            e += 2
            check_imgtags = name[s:e]
            # check the image counter, it should be equal to the step counter
            assert "{}".format(i) in check_imgtags
            # check the camera name
            assert "{}".format(dummy_camera_name) in check_imgtags

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
        assert os.path.exists(performed_measurement.measurement._log_path)
        assert os.path.isfile(performed_measurement.measurement._log_path)
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("performed_measurement")
    def test_log_row_count_is_correct(self, performed_measurement):
        """Test if there is a log has the correct number of rows."""
        
        with open(performed_measurement.measurement._log_path) as f:
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
        
        with open(performed_measurement.measurement._log_path) as f:
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
            lambda m: pylo.microscope_ready.append(m.measurement.stop),
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
            lambda m: pylo.before_record.append(m.measurement.stop),
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
            lambda m: pylo.after_record.append(m.measurement.stop),
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
        assert len(performed_measurement.before_record_time) > 0
        # check that the following events are not executed
        assert len(performed_measurement.after_record_time) == 0
        assert len(performed_measurement.measurement_ready_time) == 0

        # reset the sleep time to be random again
        setSleepTime("random")
    
    def after_stop_handler(self):
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
        pylo.after_stop.append(self.after_stop_handler)

        performed_measurement = PerformedMeasurement(0, auto_start=False)

        # start the measurement another thread
        thread = pylo.ExceptionThread(target=performed_measurement.measurement.start)
        thread.start()

        # stop the measurement
        stop_callable(performed_measurement, operation_time)

        # event is only triggered once
        assert len(self.after_stop_times) == 1
        # event is triggered immediately after the stop call
        assert math.isclose(self.after_stop_times[0], time.time(), rel_tol=0,
                            abs_tol=0.01)

        # wait until the thread is done
        thread.join()

        # check if the measurement is acutally stopped
        self.check_measurement_is_stopped(performed_measurement)

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
                lambda m: pylo.microscope_ready.append(self.throw_exception)
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
                lambda m: pylo.before_record.append(self.throw_exception)
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
                lambda m: pylo.after_record.append(self.throw_exception)
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
    
    def test_parse_series(self):
        """Test if the Measurement::_parseSeries() is correct for a single 
        series."""

        controller = DummyController()
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1}

        steps = pylo.Measurement._parseSeries(controller, start, series)

        assert len(steps) == 11

        for i, step in enumerate(steps):
            for measurement_var in controller.microscope.supported_measurement_variables:
                # make sure all the measurement variables are present in every
                # step
                assert measurement_var.unique_id in step
            
            assert step["lense-current"] == 0
            assert step["x-tilt"] == 0
            
            if i == 0:
                assert step["focus"] == 0
            else:
                assert step["focus"] == steps[i - 1]["focus"] + 1
    
    def test_parse_single_nested_series(self):
        """Test if the Measurement::_parseSeries() is correct for a series 
        that contains another series."""

        controller = DummyController()
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1, 
                  "on-each-point": {"variable": "lense-current", "start": 0, 
                                   "end": 3, "step-width": 0.1}}

        steps = pylo.Measurement._parseSeries(controller, start, series)

        assert len(steps) == 11 * 31

        for i, step in enumerate(steps):
            for measurement_var in controller.microscope.supported_measurement_variables:
                # make sure all the measurement variables are present in every
                # step
                assert measurement_var.unique_id in step
            
            assert step["x-tilt"] == 0
            
            if i % 31 == 0:
                assert step["lense-current"] == 0
            else:
                # having problems with float rounding
                assert math.isclose(step["lense-current"], 
                                    steps[i - 1]["lense-current"] + 0.1)
            
            if i // 31 == 0:
                assert step["focus"] == 0
            else:
                assert math.isclose(step["focus"], 
                                    steps[(i // 31) * 31 - 1]["focus"] + 1)
    
    def test_parse_double_nested_series(self):
        """Test if the Measurement::_parseSeries() is correct for a series 
        that contains another series and that contains another series."""

        controller = DummyController()
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1, 
                  "on-each-point": {"variable": "lense-current", "start": 0, 
                                   "end": 3, "step-width": 0.1, 
                                   "on-each-point": {"variable": "x-tilt", 
                                                     "start": -20, 
                                                     "end": 20, 
                                                     "step-width": 5}}}

        steps = pylo.Measurement._parseSeries(controller, start, series)

        assert len(steps) == 11 * 31 * 9

        for i, step in enumerate(steps):
            for measurement_var in controller.microscope.supported_measurement_variables:
                # make sure all the measurement variables are present in every
                # step
                assert measurement_var.unique_id in step
            
            if i % 9 == 0:
                assert step["x-tilt"] == -20
            else:
                # having problems with float rounding
                assert math.isclose(step["x-tilt"], 
                                    steps[i - 1]["x-tilt"] + 5)
            
            if (i // 9) % 31 == 0:
                assert step["lense-current"] == 0
            else:
                # having problems with float rounding
                assert math.isclose(step["lense-current"], 
                                    steps[(i // 9) * 9 - 1]["lense-current"] + 0.1)
            
            if i // (31 * 9) == 0:
                assert step["focus"] == 0
            else:
                assert math.isclose(step["focus"], 
                                    steps[(i // 31 // 9) * 31 * 9 - 1]["focus"] + 1)
    
    def test_parse_series_wrong_variable_raises_exception(self):
        """Test if an invalid variable id raises an exception."""
        controller = DummyController()
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "non-existing", "start": 0, "end": 10, "step-width": 1}

        with pytest.raises(ValueError):
            pylo.Measurement._parseSeries(controller, start, series)
    
    def test_parse_series_missing_key_raises_exception(self):
        """Test if missing keys raise an exception."""
        controller = DummyController()
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1}

        for key in series:
            invalid_series = copy.deepcopy(series)
            del invalid_series[key]

            with pytest.raises(KeyError):
                pylo.Measurement._parseSeries(controller, start, invalid_series)
    
    def test_parse_series_missing_key_in_subseries_raises_exception(self):
        """Test if missing keys raise an exception."""
        controller = DummyController()
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1,
                  "on-each-point": {"variable": "x-tilt", "start": -5, "end": 5,
                                   "step-width": 5}}

        for key in series["on-each-point"]:
            invalid_series = copy.deepcopy(series)
            del invalid_series["on-each-point"][key]

            with pytest.raises(KeyError):
                pylo.Measurement._parseSeries(controller, start, invalid_series)

    @pytest.mark.parametrize("step_width", (-1, 0))
    def test_parse_series_step_width_smaller_than_zero(self, step_width):
        """Test if a step with smaller or equal to zero raises an exception."""

        controller = DummyController()
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": step_width}

        with pytest.raises(ValueError):
            pylo.Measurement._parseSeries(controller, start, series)

    def test_parse_series_wrong_boundaries_raises_exception(self):
        """Test if an exception is raised when the value is out of the 
        boundaries."""
        
        controller = DummyController()
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        
        for var in controller.microscope.supported_measurement_variables:
            wrong_start_series = {"variable": var.unique_id, 
                                  "start": var.min_value - random.randint(1, 100),
                                  "end": var.max_value,
                                  "step-width": 1}
            with pytest.raises(ValueError):
                pylo.Measurement._parseSeries(controller, start, 
                                              wrong_start_series)

            wrong_end_series = {"variable": var.unique_id, 
                                "start": var.min_value,
                                "end": var.max_value + random.randint(1, 100),
                                "step-width": 1}
            with pytest.raises(ValueError):
                pylo.Measurement._parseSeries(controller, start, 
                                              wrong_end_series)

    def test_parse_series_uneven_step_width_stays_in_boundaries(self):
        """Test if the all the steps are in the boundaries if the step width 
        does not fit even times in the range between start and end
        (e.g. start=1, end=2, step-width = 0.6)."""
        
        controller = DummyController()
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        
        for var in controller.microscope.supported_measurement_variables:
            series = {"variable": var.unique_id, "start": var.min_value,
                      "end": var.max_value, 
                      "step-width": (var.max_value - var.min_value) * 2 / 3}
            
            steps = pylo.Measurement._parseSeries(controller, start, series)

            for s in steps:
                assert var.min_value <= s[var.unique_id]
                assert s[var.unique_id] <= var.max_value

    def test_parse_series_too_big_step_width_stays_in_boundaries(self):
        """Test if the all the steps are in the boundaries if the step width 
        is bigger than the range between start and end
        (e.g. start=1, end=2, step-width = 4)."""
        
        controller = DummyController()
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        
        for var in controller.microscope.supported_measurement_variables:
            series = {"variable": var.unique_id, "start": var.min_value,
                      "end": var.max_value, 
                      "step-width": (var.max_value - var.min_value) * 4}
            
            steps = pylo.Measurement._parseSeries(controller, start, series)

            for s in steps:
                assert var.min_value <= s[var.unique_id]
                assert s[var.unique_id] <= var.max_value
    
    def test_parse_series_missing_key_in_start_conditions_raises_exception(self):
        """Test if a value out of the boundaries in the start conditions raises
        an exception."""
        controller = DummyController()

        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "lense-current", "start": 0, "end": 3, "step-width": 1}

        for key in start:
            invalid_start = start.copy()
            del invalid_start[key]
            
            if key == series["variable"]:
                # if the series variable is the removed key, the start 
                # conditions are fully given because the series defines the 
                # start conditions then
                assert isinstance(
                    pylo.Measurement._parseSeries(controller, invalid_start, series),
                    (list, tuple)
                )
            else:
                with pytest.raises(KeyError):
                    pylo.Measurement._parseSeries(controller, invalid_start, series)
    
    def test_parse_series_wrong_value_in_start_conditions_raises_exception(self):
        """Test if a missing measuremnet variable in the start conditions 
        raises an exception."""
        controller = DummyController()

        # missing focus
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1}

        for var in controller.microscope.supported_measurement_variables:
            start_too_small = start.copy()
            start_too_small[var.unique_id] = var.min_value - random.randint(1, 100)

            # if the series variable is given, it defines the start conditions
            if var.unique_id == series["variable"]:
                series["start"] = start_too_small[var.unique_id]

            with pytest.raises(ValueError):
                pylo.Measurement._parseSeries(controller, start_too_small, series)
            
            start_too_big = start.copy()
            start_too_big[var.unique_id] = var.max_value + random.randint(1, 100)

            # if the series variable is given, it defines the start conditions
            if var.unique_id == series["variable"]:
                series["start"] = start_too_big[var.unique_id]

            with pytest.raises(ValueError):
                pylo.Measurement._parseSeries(controller, start_too_big, series)

if __name__ == "__main__":
    pass
