import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
import pytest
import glob
import time

import numpy as np

import pylo

pylo_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pylo")

# class DummyView(pylo.AbstractView):
class DummyView:
    def __init__(self):
        self.clear()
    
    def clear(self):
        self.shown_create_measurement_times = []
        self.ask_for_response = []
        self.error_log = []
        self.inputs = []
    
    def setAskForResponseValues(self, name_contains, response):
        self.ask_for_response.append((name_contains, response))

    def askFor(self, *inputs):
        self.inputs = inputs

        responses = []

        for i, inp in enumerate(self.inputs):
            if "name" in inp:
                for name_contains, response in self.ask_for_response:
                    if (isinstance(name_contains, str) and 
                        name_contains in inp["name"]):
                        responses.append(response)
                    elif isinstance(name_contains, (list, tuple)):
                        is_correct_name = True
                        for n in name_contains:
                            if not n in inp["name"]:
                                is_correct_name = False
                                break
                        
                        if is_correct_name:
                            responses.append(response)

            if len(responses) < i + 1:
                # no response found
                responses.append("ASKED_FOR_DEFAULT_RESPONSE")
        
        return responses
    
    def showCreateMeasurement(self):
        self.shown_create_measurement_times.append(time.time())
        
        return (
            # start conditions
            {"measurement-var": 0},
            # series definition
            {"variable": "measurement-var", "start": 0, "end": 1, "step-width": 1}
        )
    
    def showError(self, error, how_to_fix=None):
        self.error_log.append((error, how_to_fix))
        print(error, how_to_fix)
        assert False

class DummyConfiguration(pylo.AbstractConfiguration):
    def __init__(self):
        super().__init__()
    
    def getValue(self, group, key, fallback_default=True):
        self.request_log.append((group, key))
        return super().getValue(group, key, fallback_default)
    
    def loadConfiguration(self):
        self.clear()
    
    def clear(self):
        self.request_log = []
        self.configuration = {}

class DummyImage(pylo.Image):
    def saveTo(self, *args, **kwargs):
        pass

use_dummy_images = False
class DummyCamera(pylo.CameraInterface):
    def __init__(self):
        super().__init__()
        self.clear()
    
    def clear(self):
        self.init_time = time.time()
        self.recorded_images = []
    
    def recordImage(self):
        self.recorded_images.append(time.time())
        args = (np.zeros((5, 5), dtype=np.uint8), {"dummy-tag": True})
        if use_dummy_images:
            return DummyImage(*args)
        else:
            return pylo.Image(*args)
    
    def resetToSafeState(self):
        pass

class DummyMicroscope(pylo.microscopes.MicroscopeInterface):
    def __init__(self):
        super().__init__()
        self.clear()

    def clear(self):
        self.init_time = time.time()
        self.performed_steps = []

        self.supported_measurement_variables = [
            pylo.MeasurementVariable(
                "measurement-var", "Dummy Measurement Variable", -1, 1, "unit"
            )
        ]
    
    def setInLorenzMode(self, lorenz_mode):
        pass
    
    def setMeasurementVariableValue(self, id_, value):
        self.performed_steps.append((id_, value, time.time()))
    
    def resetToSafeState(self):
        pass

configuration_test_setup = [
    ({"group": "test-group", "key": "test-key", "value": "test"}, ),
    ({"group": "test-group2", "key": "test-key", "value": False}, ),
    ({"group": "test-group3", "key": "test-key3", "value": 1},
        {"group": "test-group3", "key": "test-key14", "value": 2},
        {"group": "test-group4", "key": "test-key13", "value": 3},
        {"group": "test-group3", "key": "test-key16", "value": 4},
        {"group": "test-group2", "key": "test-key14", "value": 5}),
    ({"group": "test-group2", "key": "test-key2", "description": "descr",
        "datatype": bool, "options": (True, False), "value": False}, ),
    ({"group": "test-group2", "key": "test-key2",
        "datatype": float, "options": (1, 1.1, 1.2, 1.3), "value": 2.2}, ),
    ({"group": "test-group2", "key": "test-key2", "description": "descr2",
        "value": "test2"}, ),
    ({"group": "test-group3", "key": "test-key3", "description": "d1",
        "datatype": str, "options": ("a", "b", "c"), "value": "a"},
        {"group": "test-group3", "key": "test-key4", "description": "d2",
        "datatype": int, "options": (1, 2, 3, 4, 5, 6, 7), "value": 8},
        {"group": "test-group4", "key": "test-key3", "description": "d3",
        "datatype": float, "options": (0.1, 0.2, 0.3, 0.5), "value": 0.6},
        {"group": "test-group3", "key": "test-key5",
        "datatype": bool, "value": True})
]

@pytest.fixture()
def controller():
    pylo.config.CONFIGURATION = DummyConfiguration()
    pylo.config.CONFIGURATION.clear()
    pylo.config.VIEW = DummyView()
    controller = pylo.Controller()

    yield controller

    controller.view.clear()
    controller.configuration.clear()


class TestController:
    @pytest.mark.usefixtures("controller")
    @pytest.mark.parametrize("lookup", configuration_test_setup)
    def test_get_configuration_value_or_ask_value_exists(self, controller, lookup):
        """Test if the getConfigurationValueOrAsk() function returns the corect
        values in the correct order if the values are given."""
        
        self.check_get_configuration_value_or_ask(controller, lookup, 
                                                  [True] * len(lookup))
                                                
    @pytest.mark.usefixtures("controller")
    @pytest.mark.parametrize("lookup", configuration_test_setup)
    def test_get_configuration_value_or_ask_value_not_exists(self, controller, lookup):
        """Test if the getConfigurationValueOrAsk() function asks for the 
        values if they do not exist."""

        self.check_get_configuration_value_or_ask(controller, lookup, 
                                                  [False] * len(lookup))
                                                
    @pytest.mark.usefixtures("controller")
    @pytest.mark.parametrize("lookup", configuration_test_setup)
    def test_get_configuration_value_or_ask_value_partly_exists(self, controller, lookup):
        """Test if the getConfigurationValueOrAsk() function asks for the 
        missing values if some exist and others do not."""

        if len(lookup) == 1:
            exist = [random.random() >= 0.5]
        else:
            # make sure there is at least one time True and one time False
            exist = [True, False]
            # add more random values
            exist += [random.random() >= 0.5 for i in range(len(lookup) - 2)]
            # randomize order
            random.shuffle(exist)

        self.check_get_configuration_value_or_ask(controller, lookup, exist)
    
    def check_get_configuration_value_or_ask(self, controller, lookup, exist_in_config):
        """Perform the test for the getConfigurationValuesOrAsk() function.

        Parameters
        ----------
        controller : Controller
            The controller
        lookup : list of dicts
            The lookup dict
        exist_in_config : list of bool
            A list whether the lookup should exist in the configuration or not
        """

        # create the parameter for the getConfigurationValuesOrAsk() function
        config_lookup = []

        # prepare the configuration and the config_lookup
        for lookup_dir, exists in zip(lookup, exist_in_config):
            if exists:
                # set the value
                controller.configuration.setValue(lookup_dir["group"], 
                                                  lookup_dir["key"], 
                                                  lookup_dir["value"])
            else:
                # define the configuration options so the datatype ect. are 
                # known
                controller.configuration.addConfigurationOption(
                    lookup_dir["group"], 
                    lookup_dir["key"],
                    datatype=(lookup_dir["datatype"] if "datatype" in lookup_dir 
                            else None),
                    description=(lookup_dir["description"] if "description" in lookup_dir 
                                else None)
                )

                # set the responses for the view ask
                controller.view.setAskForResponseValues((lookup_dir["key"], 
                                                        lookup_dir["group"]),
                                                        lookup_dir["value"])

            l = [lookup_dir["group"], lookup_dir["key"]]
            if "options" in lookup_dir:
                l.append(lookup_dir["options"])
            
            config_lookup.append(l)

        # get the values
        values = controller.getConfigurationValuesOrAsk(*config_lookup)
        ask_counter = 0

        for i, (l, e) in enumerate(zip(lookup, exist_in_config)):
            if not e:
                # check if the key and the group were asked for
                assert isinstance(controller.view.inputs[ask_counter]["name"], str)
                assert l["key"] in controller.view.inputs[ask_counter]["name"]
                assert l["group"] in controller.view.inputs[ask_counter]["name"]

                # check if the datatype was passed if there is one
                if "datatype" in l:
                    assert "datatype" in controller.view.inputs[ask_counter]
                    assert l["datatype"] == controller.view.inputs[ask_counter]["datatype"]

                # check if the desciption was passed if there is one
                if "description" in l:
                    assert "description" in controller.view.inputs[ask_counter]
                    assert l["description"] == controller.view.inputs[ask_counter]["description"]

                # check if the options was passed if there are some
                if "options" in l:
                    assert "options" in controller.view.inputs[ask_counter]
                    assert (tuple(l["options"]) == 
                            tuple(controller.view.inputs[ask_counter]["options"]))
                
                ask_counter += 1
            
            # check if the value exists (now) in the configuration
            assert values[i] == controller.configuration.getValue(l["group"], 
                                                                    l["key"])
            # check if the returned value is correct
            assert values[i] == l["value"]
        
    def create_dummy_class_file(self, directory):
        """Creates a python file that defines two classes and saves it to the 
        given directory.

        Raises
        ------
        OSError
            When the file cannot be created

        Parameters
        ----------
        directory : str
            The directory to save the file to
        
        Returns
        -------
        str
            The file name
        str
            The full file path (including the file name)
        str
            The module name
        str
            The class name (the second class has the same name with a "2"
            appended)
        """

        class_name = "ControllerTestDummyClass{}C".format(random.randint(0, 99999999))
        module = class_name.lower()
        filename = module + ".py"

        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)

        f = open(path, "w+")
        f.write(("class {cn}:\n" + 
                    "\tdef __init__(self, *args):\n" + 
                        "\t\tself.dummy_value = \"dummy value\"\n" + 
                        "\t\tself.constructor_args = args\n"
                "\n" + 
                    "\tdef dummy_func(self):\n" + 
                        "\t\treturn True\n"
                "\n" + 
                "\n" + 
                "class {cn}2:\n" + 
                    "\tdef __init__(self, *args):\n" + 
                        "\t\tself.constructor_args = args\n" + 
                "\n" + 
                "\n" + 
                "thisisnotaclass = True").format(cn=class_name))
        f.close()

        return filename, path, module, class_name
    
    def remove_test_files(self):
        """Removes the files for the dynamic import test."""

        root = os.path.dirname(pylo_root)
        tmp_path = os.path.join(root, "test", "tmp_test_files")
        
        files = (
            # all the controller test files
            glob.glob(os.path.join(root, "controllertestdummyclass*.py")) + 
            glob.glob(os.path.join(root, "pylo", "controllertestdummyclass*.py")) + 
            glob.glob(os.path.join(root, "test", "controllertestdummyclass*.py")) + 
            glob.glob(os.path.join(root, "pylo", "microscopes", "controllertestdummyclass*.py")) + 
            # all the files in tmp_test_files
            glob.glob(os.path.join(tmp_path, "*.*"))
        )

        for f in files:
            os.remove(f)
        
        if os.path.isdir(tmp_path):
            os.removedirs(tmp_path)
    
    def check_dynamic_created_object(self, obj, class_name, constructor_args=None):
        """Check if the `obj` is created correctly."""

        assert isinstance(obj, object)
        assert hasattr(obj, "__class__")
        assert hasattr(obj.__class__, "__name__")
        assert obj.__class__.__name__ == class_name

        if constructor_args is not None:
            assert obj.constructor_args == constructor_args
    
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_root(self, controller):
        """Test whether the _dynamicCreateClass() function works for a file
        in the pylo root directory."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        obj = controller._dynamicCreateClass("dummy-test-module-name", 
                                             "dummy-test-class-name")
        
        self.check_dynamic_created_object(obj, class_name)
        
        self.remove_test_files()
    
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_root_with_extension(self, controller):
        """Test whether the _dynamicCreateClass() function works for a file
        in the pylo root directory."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", module + ".py")
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        obj = controller._dynamicCreateClass("dummy-test-module-name", 
                                             "dummy-test-class-name")
        
        self.check_dynamic_created_object(obj, class_name)
        
        self.remove_test_files()
    
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_root_with_args(self, controller):
        """Test whether the _dynamicCreateClass() function works with 
        constructor arguments."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        args = ("A", "B", "C")
        obj = controller._dynamicCreateClass("dummy-test-module-name", 
                                             "dummy-test-class-name",
                                             constructor_args=args)
        
        self.check_dynamic_created_object(obj, class_name, args)
        
        self.remove_test_files()
    
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_root_with_args_and_class_2(self, controller):
        """Test whether the _dynamicCreateClass() function works with two 
        classes loaded form the same source."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)
        class_name2 = class_name + "2"

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        controller.configuration.setValue("setup", "dummy-test-module-name2", module)
        controller.configuration.setValue("setup", "dummy-test-class-name2", class_name2)

        args1 = ("A", "B", "C")
        obj1 = controller._dynamicCreateClass("dummy-test-module-name", 
                                             "dummy-test-class-name",
                                             constructor_args=args1)
        args2 = ("D", "E", "F")
        obj2 = controller._dynamicCreateClass("dummy-test-module-name2", 
                                             "dummy-test-class-name2",
                                             constructor_args=args2)
        
        self.check_dynamic_created_object(obj1, class_name, args1)
        self.check_dynamic_created_object(obj2, class_name2, args2)
        
        self.remove_test_files()

    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_submodule(self, controller):
        """Test whether the _dynamicCreateClass() function works for a file
        in the micrsocopes subdirectory."""

        path = os.path.join(pylo_root, "microscopes")
        filename, path, module, class_name = self.create_dummy_class_file(path)

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        obj = controller._dynamicCreateClass("dummy-test-module-name", 
                                             "dummy-test-class-name")
        
        self.check_dynamic_created_object(obj, class_name)
        
        self.remove_test_files()

    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_cwd(self, controller):
        """Test whether the _dynamicCreateClass() function works for a file
        in the current working directory."""

        # this should be the current working directory
        path = os.getcwd()
        try:
            filename, path, module, class_name = self.create_dummy_class_file(path)
        except OSError:
            pytest.skip("The test file {} could not be created. Cannot test " + 
                        "importing if the file does not exist.")

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        obj = controller._dynamicCreateClass("dummy-test-module-name", 
                                             "dummy-test-class-name")
        
        self.check_dynamic_created_object(obj, class_name)
        
        self.remove_test_files()

    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_test(self, controller):
        """Test whether the _dynamicCreateClass() function works for a file
        in the current working directory."""

        # this should be the current working directory
        path = os.path.dirname(__file__)
        try:
            filename, path, module, class_name = self.create_dummy_class_file(path)
        except OSError:
            pytest.skip("The test file {} could not be created. Cannot test " + 
                        "importing if the file does not exist.")

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        obj = controller._dynamicCreateClass("dummy-test-module-name", 
                                             "dummy-test-class-name")
        
        self.check_dynamic_created_object(obj, class_name)
        
        self.remove_test_files()

    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_module_does_not_exist(self, controller):
        """Test whether the _dynamicCreateClass() function raises an exception
        when the module does not exist."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", "thisdoesnotexist")
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        with pytest.raises(ModuleNotFoundError):
            controller._dynamicCreateClass("dummy-test-module-name", 
                                           "dummy-test-class-name")

        self.remove_test_files()
        
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_class_does_not_exist(self, controller):
        """Test whether the _dynamicCreateClass() function raises an exception
        when the class does not exist."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", "thisdoesnotexist")

        with pytest.raises(AttributeError):
            controller._dynamicCreateClass("dummy-test-module-name", 
                                           "dummy-test-class-name")

        self.remove_test_files()
        
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_class_is_not_a_class(self, controller):
        """Test whether the _dynamicCreateClass() function raises an exception
        when the class is not a class."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", "thisisnotaclass")

        with pytest.raises((NameError, TypeError)):
            controller._dynamicCreateClass("dummy-test-module-name", 
                                           "dummy-test-class-name")

        self.remove_test_files()
    
    def before_init_handler(self):
        """The event handler for the before_init event."""
        self.before_init_times.append(time.time())
    
    def init_ready_handler(self):
        """The event handler for the init_ready event."""
        self.init_ready_times.append(time.time())
    
    def user_ready_handler(self):
        """The event handler for the user_ready event."""
        self.user_ready_times.append(time.time())
    
    def series_ready_handler(self):
        """The event handler for the series_ready event."""
        self.series_ready_times.append(time.time())
    
    def init_start_program_test(self, controller, save_files=True, change_save_path=True):
        """Initialize for testing the startProgram() function and execute the 
        function."""
        global use_dummy_images

        # prepare event time storage
        self.before_init_times = []
        self.init_ready_times = []
        self.user_ready_times = []
        self.series_ready_times = []

        # clear events
        pylo.before_init.clear()
        pylo.init_ready.clear()
        pylo.user_ready.clear()
        pylo.series_ready.clear()

        # add event handlers
        pylo.before_init.append(self.before_init_handler)
        pylo.init_ready.append(self.init_ready_handler)
        pylo.user_ready.append(self.user_ready_handler)
        pylo.series_ready.append(self.series_ready_handler)

        # define the microscope to use
        controller.configuration.setValue("setup", "microscope-module", "test_controller.py")
        controller.configuration.setValue("setup", "microscope-class", "DummyMicroscope")

        # define the camera to use
        controller.configuration.setValue("setup", "camera-module", "test_controller.py")
        controller.configuration.setValue("setup", "camera-class", "DummyCamera")

        if change_save_path:
            # # define the save path
            tmp_path = os.path.join(os.path.dirname(pylo_root), "test", "tmp_test_files")
            os.makedirs(tmp_path, exist_ok=True)
            controller.configuration.setValue("measurement", "save-directory", tmp_path)
        
        use_dummy_images = not save_files

        self.start_time = time.time()
        controller.startProgramLoop()
    
    def raise_stop_program(self):
        raise pylo.StopProgram

    @pytest.mark.usefixtures("controller")
    def test_measurement_save_paths_default(self, controller):
        """Test if the save directory and file name are correct."""
        self.init_start_program_test(controller, save_files=False, 
                                     change_save_path=False)

        assert (controller.measurement.save_dir == 
                pylo.config.DEFAULT_SAVE_DIRECTORY)
        assert (controller.measurement.name_format == 
                pylo.config.DEFAULT_SAVE_FILE_NAME)

    @pytest.mark.usefixtures("controller")
    def test_measurement_save_paths_custom(self, controller):
        """Test if the save directory and file name can be modified correctly 
        by changing the settings."""
        
        path = os.path.join(os.path.dirname(pylo_root), "test", "tmp_test_files")
        os.makedirs(path, exist_ok=True)
        name_format = "{counter}-dummy-file.tif"

        controller.configuration.setValue("measurement", "save-directory", path)
        controller.configuration.setValue("measurement", "save-file-format", name_format)

        self.init_start_program_test(controller, save_files=False, 
                                     change_save_path=False)

        assert controller.measurement.save_dir == path
        assert controller.measurement.name_format == name_format

        self.remove_test_files()

    @pytest.mark.usefixtures("controller")
    def test_event_times(self, controller):
        """Test if all events are fired, test if the events are fired in the 
        correct order."""

        self.init_start_program_test(controller)

        # check if all events are executed exactly one time
        assert len(self.before_init_times) == 1
        assert len(self.init_ready_times) == 1
        assert len(self.user_ready_times) == 1
        assert len(self.series_ready_times) == 1

        # check the time order of the events is ready
        assert self.start_time <= self.before_init_times[0]
        assert self.before_init_times[0] <= self.init_ready_times[0]
        assert self.init_ready_times[0] <= self.user_ready_times[0]
        assert self.user_ready_times[0] <= self.series_ready_times[0]

        # test if the init event is fired before the microscope and camera are
        # created
        assert controller.microscope.init_time <= self.init_ready_times[0]
        assert controller.camera.init_time <= self.init_ready_times[0]
    
    @pytest.mark.usefixtures("controller")
    def test_microscope_from_configuration(self, controller):
        """Test if the microscope is asked from the configuration."""
        self.init_start_program_test(controller)

        # check if mircoscope is asked from the configuration
        assert ("setup", "microscope-module") in controller.configuration.request_log
        assert ("setup", "microscope-class") in controller.configuration.request_log

    @pytest.mark.usefixtures("controller")
    def test_camera_from_configuration(self, controller):
        """Test if the camera is asked from the configuration."""
        self.init_start_program_test(controller)

        # check if camera is asked from the configuration
        assert ("setup", "camera-module") in controller.configuration.request_log
        assert ("setup", "camera-class") in controller.configuration.request_log

    @pytest.mark.usefixtures("controller")
    def test_microscope_and_camera_are_valid(self, controller):
        """Test if microscope and camera are valid objects."""
        self.init_start_program_test(controller)

        # check mircoscope and camera are valid
        assert isinstance(controller.microscope, DummyMicroscope)
        assert isinstance(controller.camera, DummyCamera)
    
    @pytest.mark.usefixtures("controller")
    def test_show_create_measurement_is_executed(self, controller):
        """Test whether the view is instructed to show the create measurement 
        view."""
        self.init_start_program_test(controller)

        # shown exactly one time
        assert len(controller.view.shown_create_measurement_times) == 1

        # shown in the correct time order
        assert (self.init_ready_times[0] <= 
                controller.view.shown_create_measurement_times[0])
        assert (controller.view.shown_create_measurement_times[0] <= 
                self.user_ready_times[0])
        assert (controller.microscope.init_time <= 
                controller.view.shown_create_measurement_times[0])
        assert (controller.camera.init_time <= 
                controller.view.shown_create_measurement_times[0])
    
    @pytest.mark.usefixtures("controller")
    def test_measurement_is_valid(self, controller):
        """Test whether a valid measurement object is received (the measurement
        object creation function is tested in test_measurement.py)."""
        self.init_start_program_test(controller)

        # shown exactly one time
        assert isinstance(controller.measurement, pylo.Measurement)
