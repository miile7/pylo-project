import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
import pytest
import math
import glob
import time

import numpy as np

import pylo
import pylo.config

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

def remove_dirs(directories=None):
    """Remove all given directories recursively with files inside."""
    if not isinstance(directories, (list, tuple)):
        directories = glob.glob(os.path.join(test_root, "tmp-test-controller-*"))
    
    for directory in directories:
        if os.path.exists(directory):
            directory = str(directory)
            for f in os.listdir(directory):
                path = os.path.join(directory, f)
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    remove_dirs((path), )
        
            os.removedirs(directory)

root = os.path.dirname(os.path.dirname(__file__))
pylo_root = os.path.join(root, "pylo")
test_root = os.path.join(os.path.dirname(__file__))

# clear all test directories
remove_dirs()

controller_tmp_path = os.path.join(test_root, "tmp-test-controller-{}".format(random.randint(0, 30)))

os.makedirs(controller_tmp_path, exist_ok=True)

pylo.config.DEFAULT_LOG_PATH = os.path.join(controller_tmp_path, "measurement.log")
pylo.config.DEFAULT_INI_PATH = os.path.join(controller_tmp_path, "configuration.ini")

class DummyViewShowsError(AssertionError):
    pass

class DummyView(pylo.AbstractView):
    def __init__(self):
        self.clear()
    
    def clear(self):
        self.shown_create_measurement_times = []
        # contains the comparator at index 0 (one or more strings that have to
        # be in the name it is asked for) or a callable, contains the repsonse
        # or a callable at index 1
        self.ask_for_response = []
        self.error_log = []
        self.inputs = []
        self.measurement_to_create = (
            # start conditions
            {"measurement-var": 0},
            # series definition
            {"variable": "measurement-var", "start": 0, "end": 1, "step-width": 1}
        )
    
    def _updateRunning(self):
        pass
    
    def askFor(self, *inputs):
        self.inputs = inputs

        responses = []

        for i, inp in enumerate(self.inputs):
            if "name" in inp:
                for name_contains, response in self.ask_for_response:
                    is_correct_name = False

                    if (isinstance(name_contains, str) and 
                        name_contains in inp["name"]):
                        is_correct_name = True
                    elif isinstance(name_contains, (list, tuple)):
                        is_correct_name = True
                        for n in name_contains:
                            if not n in inp["name"]:
                                is_correct_name = False
                                break
                    elif callable(name_contains) and name_contains(inp):
                        is_correct_name = True

                    if is_correct_name:
                        if callable(response):
                            response = response(inp)
                        
                        responses.append(response)

            if len(responses) < i + 1:
                # no response found
                responses.append("ASKED_FOR_DEFAULT_RESPONSE")
        
        return responses
    
    def showCreateMeasurement(self, *args, **kwargs):
        self.shown_create_measurement_times.append(time.time())
        
        ret = self.measurement_to_create
        if callable(ret):
            ret = ret()

        return ret
    
    def showError(self, error, how_to_fix=None):
        self.error_log.append((error, how_to_fix))
        if isinstance(error, Exception):
            name = error.__class__.__name__
        else:
            name = "Error"

        print("DummyView::showError() is called.")
        print("\t{}: {}".format(name, error))
        print("\tFix: {}".format(how_to_fix))
        
        # display errors, if they are inteded use pytest.raises()
        if isinstance(error, Exception):
            import traceback
            traceback.print_exc()

            raise DummyViewShowsError("{}".format(error)).with_traceback(error.__traceback__)
        else:
            raise DummyViewShowsError(error)
    
    def print(self, *inputs, sep=" ", end="\n", inset=""):
        print(*inputs, sep=sep, end=end)

class DummyConfiguration(pylo.AbstractConfiguration):
    def __init__(self):
        super().__init__()
    
    def getValue(self, group, key, fallback_default=True):
        self.request_log.append((group, key, time.time()))
        return super().getValue(group, key, fallback_default)
    
    def loadConfiguration(self):
        self.clear()
    
    def saveConfiguration(self):
        pass
    
    def clear(self):
        self.request_log = []
        self.configuration = {}

class DummyImage(pylo.Image):
    def saveTo(self, *args, **kwargs):
        pass

use_dummy_images = False
class DummyCamera(pylo.cameras.CameraInterface):
    def __init__(self, controller):
        super().__init__(controller)
        self.clear()
    
    def clear(self):
        self.init_time = time.time()
        self.recorded_images = []
    
    def recordImage(self):
        self.recorded_images.append(time.time())
        img_data = (np.random.rand(5, 5) * 255).astype(dtype=np.uint8)
        args = (img_data, {"dummy-tag": True})
        if use_dummy_images:
            return DummyImage(*args)
        else:
            return pylo.Image(*args)
    
    def resetToSafeState(self):
        pass

measurement_duration_time = -1
class DummyMicroscope(pylo.microscopes.MicroscopeInterface):
    def __init__(self, controller):
        super().__init__(controller)
        self.clear()

    def clear(self):
        self.init_time = time.time()
        self.performed_steps = []

        self.supported_measurement_variables = [
            pylo.MeasurementVariable(
                "measurement-var", "Dummy Measurement Variable", -1, 1, "unit"
            )
        ]
    
    def setInLorentzMode(self, lorentz_mode):
        pass
    
    def setMeasurementVariableValue(self, id_, value):
        self.performed_steps.append((id_, value, time.time()))

        if measurement_duration_time > 0:
            time.sleep(measurement_duration_time)
    
    def getMeasurementVariableValue(self, id_):
        for k, v, t in reversed(self.performed_steps):
            if id_ == k:
                return v
            
        return None
    
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
        "datatype": bool, "value": False}, ),
    ({"group": "test-group2", "key": "test-key2",
        "datatype": pylo.OptionDatatype((1, 1.1, 1.2, 1.3)), "value": 1.2}, ),
    ({"group": "test-group2", "key": "test-key2", "description": "descr2",
        "value": "test2"}, ),
    ({"group": "test-group3", "key": "test-key3", "description": "d1",
        "datatype": pylo.OptionDatatype(("a", "b", "c")), "value": "a"},
        {"group": "test-group3", "key": "test-key4", "description": "d2",
        "datatype": pylo.OptionDatatype((1, 2, 3, 4, 5, 6, 7)), "value": 1},
        {"group": "test-group4", "key": "test-key3", "description": "d3",
        "datatype": pylo.OptionDatatype((0.1, 0.2, 0.3, 0.5)), "value": 0.3},
        {"group": "test-group3", "key": "test-key5",
        "datatype": bool, "value": True})
]

@pytest.fixture()
def controller():
    global measurement_duration_time

    measurement_duration_time = -1
    pylo.config.CONFIGURATION = DummyConfiguration()
    pylo.config.CONFIGURATION.clear()
    pylo.config.VIEW = DummyView()
    controller = pylo.Controller()

    yield controller

    # clear events
    pylo.before_start.clear()
    pylo.before_init.clear()
    pylo.init_ready.clear()
    pylo.user_ready.clear()
    pylo.series_ready.clear()
    pylo.microscope_ready.clear()
    pylo.before_record.clear()
    pylo.after_record.clear()
    pylo.measurement_ready.clear()

    controller.view.clear()
    controller.configuration.clear()

class TestController:
    @classmethod
    def teardown_class(cls):
        remove_dirs()

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
                args = {}
                if "datatype" in lookup_dir:
                    args["datatype"] = lookup_dir["datatype"]
                if "description" in lookup_dir:
                    args["description"] = lookup_dir["description"]
                controller.configuration.addConfigurationOption(
                    lookup_dir["group"], 
                    lookup_dir["key"],
                    **args
                )

                # set the responses for the view ask
                controller.view.ask_for_response.append(((lookup_dir["key"], 
                                                          lookup_dir["group"]),
                                                          lookup_dir["value"]))

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

        directory = str(directory)

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
    
    def clear_dummy_class_files(self, path):
        """Remove the given file."""
        if os.path.exists(path):
            if (os.path.isfile(path) and 
                os.path.basename(path).startswith("controllertestdummyclass")):
                os.remove(path)
            else:
                raise OSError("Not removing '{}' because it probably is not " + 
                              "a controller dummy test class.")
    
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
        """Test whether the _dynamicGetClasses() function works for a file
        in the pylo root directory."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        # wait a short time, otherwise the module is sometimes not found
        time.sleep(0.1)
        obj = controller._dynamicGetClasses(("dummy-test-module-name", 
                                             "dummy-test-class-name"))

        assert isinstance(obj, (list, tuple))
        assert len(obj) == 1

        obj = obj[0]
        assert isinstance(obj, type)

        obj = controller._dynamicCreateClass(obj)
        self.check_dynamic_created_object(obj, class_name)
        self.clear_dummy_class_files(path)
    
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_root_with_extension(self, controller):
        """Test whether the _dynamicGetClasses() function works for a file
        in the pylo root directory."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", module + ".py")
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        # wait a short time, otherwise the module is sometimes not found
        time.sleep(0.1)
        obj = controller._dynamicGetClasses(("dummy-test-module-name", 
                                             "dummy-test-class-name"))

        assert isinstance(obj, (list, tuple))
        assert len(obj) == 1

        obj = obj[0]
        assert isinstance(obj, type)
        
        obj = controller._dynamicCreateClass(obj)
        self.check_dynamic_created_object(obj, class_name)
        self.clear_dummy_class_files(path)
    
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_root_with_args(self, controller):
        """Test whether the _dynamicGetClasses() function works with 
        constructor arguments."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        # wait a short time, otherwise the module is sometimes not found
        time.sleep(0.1)
        obj = controller._dynamicGetClasses(("dummy-test-module-name", 
                                             "dummy-test-class-name"))
        args = ("A", "B", "C")

        assert isinstance(obj, (list, tuple))
        assert len(obj) == 1

        obj = obj[0]
        assert isinstance(obj, type)
        obj = controller._dynamicCreateClass(obj, constructor_args=args)
        
        self.check_dynamic_created_object(obj, class_name, args)
        self.clear_dummy_class_files(path)
    
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_root_with_args_and_class_2(self, controller):
        """Test whether the _dynamicGetClasses() function works with two 
        classes loaded form the same source."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)
        class_name2 = class_name + "2"

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        controller.configuration.setValue("setup", "dummy-test-module-name2", module)
        controller.configuration.setValue("setup", "dummy-test-class-name2", class_name2)

        # wait a short time, otherwise the module is sometimes not found
        time.sleep(0.1)

        args1 = ("A", "B", "C")
        args2 = ("D", "E", "F")
        obj = controller._dynamicGetClasses(
            ("dummy-test-module-name", "dummy-test-class-name"),
            ("dummy-test-module-name2", "dummy-test-class-name2")
        )

        assert isinstance(obj, (list, tuple))
        assert len(obj) == 2

        obj1, obj2 = obj
        assert isinstance(obj1, type)
        assert isinstance(obj2, type)

        obj1 = controller._dynamicCreateClass(obj1, constructor_args=args1)
        obj2 = controller._dynamicCreateClass(obj2, constructor_args=args2)
        
        self.check_dynamic_created_object(obj1, class_name, args1)
        self.check_dynamic_created_object(obj2, class_name2, args2)
        self.clear_dummy_class_files(path)

    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_submodule(self, controller):
        """Test whether the _dynamicGetClasses() function works for a file
        in the micrsocopes subdirectory."""

        path = os.path.join(pylo_root, "microscopes")
        filename, path, module, class_name = self.create_dummy_class_file(path)

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        # wait a short time, otherwise the module is sometimes not found
        time.sleep(0.1)
        obj = controller._dynamicGetClasses(("dummy-test-module-name", 
                                             "dummy-test-class-name"))
        
        assert isinstance(obj, (list, tuple))
        assert len(obj) == 1

        obj = obj[0]
        assert isinstance(obj, type)
        obj = controller._dynamicCreateClass(obj)
        
        self.check_dynamic_created_object(obj, class_name)
        self.clear_dummy_class_files(path)

    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_cwd(self, controller):
        """Test whether the _dynamicGetClasses() function works for a file
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

        # wait a short time, otherwise the module is sometimes not found
        time.sleep(0.1)
        obj = controller._dynamicGetClasses(("dummy-test-module-name", 
                                             "dummy-test-class-name"))
        
        assert isinstance(obj, (list, tuple))
        assert len(obj) == 1

        obj = obj[0]
        assert isinstance(obj, type)
        obj = controller._dynamicCreateClass(obj)
        
        self.check_dynamic_created_object(obj, class_name)
        self.clear_dummy_class_files(path)

    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_in_test(self, controller):
        """Test whether the _dynamicGetClasses() function works for a file
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

        # wait a short time, otherwise the module is sometimes not found
        time.sleep(0.1)
        obj = controller._dynamicGetClasses(("dummy-test-module-name", 
                                             "dummy-test-class-name"))
        
        assert isinstance(obj, (list, tuple))
        assert len(obj) == 1

        obj = obj[0]
        assert isinstance(obj, type)
        obj = controller._dynamicCreateClass(obj)
        
        self.check_dynamic_created_object(obj, class_name)
        self.clear_dummy_class_files(path)

    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_module_does_not_exist(self, controller):
        """Test whether the _dynamicGetClasses() function raises an exception
        when the module does not exist."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", "thisdoesnotexist")
        controller.configuration.setValue("setup", "dummy-test-class-name", class_name)

        # wait a short time, otherwise the module is sometimes not found
        time.sleep(0.1)
        with pytest.raises((ModuleNotFoundError, ImportError)):
            # python <3.6 raises an ImportError
            controller._dynamicGetClasses(("dummy-test-module-name", 
                                           "dummy-test-class-name"))
        self.clear_dummy_class_files(path)
        
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_class_does_not_exist(self, controller):
        """Test whether the _dynamicGetClasses() function raises an exception
        when the class does not exist."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", "thisdoesnotexist")

        # wait a short time, otherwise the module is sometimes not found
        time.sleep(0.1)
        with pytest.raises((AttributeError, ImportError)):
            # python <3.6 raises an import error
            controller._dynamicGetClasses(("dummy-test-module-name", 
                                           "dummy-test-class-name"))
        self.clear_dummy_class_files(path)
        
    @pytest.mark.usefixtures("controller")
    def test_dynamic_create_class_class_is_not_a_class(self, controller):
        """Test whether the _dynamicGetClasses() function raises an exception
        when the class is not a class."""

        filename, path, module, class_name = self.create_dummy_class_file(pylo_root)

        controller.configuration.setValue("setup", "dummy-test-module-name", module)
        controller.configuration.setValue("setup", "dummy-test-class-name", "thisisnotaclass")

        # wait a short time, otherwise the module is sometimes not found
        time.sleep(0.1)
        with pytest.raises((NameError, TypeError, ImportError)):
            # python <3.6 raises an import error
            controller._dynamicGetClasses(("dummy-test-module-name", 
                                           "dummy-test-class-name"))
        self.clear_dummy_class_files(path)
    
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
    
    def init_start_program_test(self, controller, save_path, save_files=True, 
                                change_save_path=True, change_microscope=True,
                                change_camera=True, before_start=None,
                                wait_for_finish=True):
        """Initialize for testing the startProgramLoop() function and execute 
        startProgramLoop() function.
        
        Parameters
        ----------
        controller : Controller
            The controller to start the program loop of
        save_files : bool
            Whether to save the files, this changes the `DummyCamera` to use 
            `DummyImage`s or normal `pylo.Image`s, the `DummyImage`s do not 
            have a (valid) `Image::saveTo()` function.
        change_save_path : bool
            Whether to change the path of the images to save to the test tmp
            dir or not
        change_microscope : bool
            Whether to change the 'microscope-module' and 'microscope-class' 
            configurations so the `DummyMicroscope` in this file will be used
        change_camera : bool
            Whether to change the 'camera-module' and 'camera-class' 
            configurations so the `DummyCamera` in this file will be used
        before_start : callable
            Executed right before the program loop is started
        wait_for_finish : bool
            Whether to wait until the program has finished
        """
        global use_dummy_images

        # prepare event time storage
        self.before_init_times = []
        self.init_ready_times = []
        self.user_ready_times = []
        self.series_ready_times = []
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

        if change_microscope:
            # define the microscope to use
            controller.configuration.setValue("setup", "microscope-module", "test_controller.py")
            controller.configuration.setValue("setup", "microscope-class", "DummyMicroscope")

        if change_camera:
            # define the camera to use
            controller.configuration.setValue("setup", "camera-module", "test_controller.py")
            controller.configuration.setValue("setup", "camera-class", "DummyCamera")

        if change_save_path:
            controller.configuration.setValue("measurement", "save-directory", save_path)
            controller.configuration.setValue("measurement", "save-file-format", "{counter}-dummy-img.tif")
        
        use_dummy_images = not save_files

        if callable(before_start):
            before_start()

        self.start_time = time.time()
        controller.startProgramLoop()

        if wait_for_finish:
            controller.waitForProgram()
    
    def raise_stop_program(self, *args, **kwargs):
        """Raise a StopProgram Exception."""
        raise pylo.StopProgram

    @pytest.mark.usefixtures("controller")
    def test_measurement_save_paths_default(self, tmp_path, controller):
        """Test if the save directory and file name are correct."""
        self.init_start_program_test(controller, tmp_path, save_files=False, 
                                     change_save_path=False)

        assert (controller.measurement.save_dir == 
                pylo.config.DEFAULT_SAVE_DIRECTORY)
        assert (controller.measurement.name_format == 
                pylo.config.DEFAULT_SAVE_FILE_NAME)

    @pytest.mark.usefixtures("controller")
    def test_measurement_save_paths_custom(self, tmp_path, controller):
        """Test if the save directory and file name can be modified correctly 
        by changing the settings."""

        name_format = "{counter}-dummy-file.tif"

        tmp_path = str(tmp_path)

        controller.configuration.setValue(
            "measurement", "save-directory", tmp_path
        )
        controller.configuration.setValue(
            "measurement", "save-file-format", name_format
        )

        self.init_start_program_test(controller, tmp_path, save_files=False, 
                                     change_save_path=False)

        assert (os.path.realpath(controller.measurement.save_dir) == 
                os.path.realpath(tmp_path))
        assert controller.measurement.name_format == name_format

    @pytest.mark.usefixtures("controller")
    def test_event_times(self, tmp_path, controller):
        """Test if all events are fired, test if the events are fired in the 
        correct order."""

        self.init_start_program_test(controller, tmp_path)

        # check if all events are executed exactly one time
        assert len(self.before_init_times) == 1
        assert len(self.init_ready_times) == 1
        assert len(self.user_ready_times) == 1
        assert len(self.series_ready_times) == 1

        # check the time order of the events is ready
        assert self.start_time <= min(self.before_init_times)
        assert max(self.before_init_times) <= min(self.init_ready_times)
        assert max(self.init_ready_times) <= min(self.user_ready_times)
        assert max(self.user_ready_times) <= min(self.series_ready_times)

        # test if the init event is fired before the microscope and camera are
        # created
        assert controller.microscope.init_time <= self.init_ready_times[0]
        assert controller.camera.init_time <= self.init_ready_times[0]
    
    @pytest.mark.usefixtures("controller")
    def test_microscope_from_configuration(self, tmp_path, controller):
        """Test if the microscope is asked from the configuration."""
        self.init_start_program_test(controller, tmp_path)

        # contains the request with group at index 0 and key at index 1
        requests = [r[:2] for r in controller.configuration.request_log]

        # check if mircoscope is asked from the configuration
        assert ("setup", "microscope-module") in requests
        assert ("setup", "microscope-class") in requests

    @pytest.mark.usefixtures("controller")
    def test_camera_from_configuration(self, tmp_path, controller):
        """Test if the camera is asked from the configuration."""
        self.init_start_program_test(controller, tmp_path)

        # contains the request with group at index 0 and key at index 1
        requests = [r[:2] for r in controller.configuration.request_log]

        # check if camera is asked from the configuration
        assert ("setup", "camera-module") in requests
        assert ("setup", "camera-class") in requests

    @pytest.mark.usefixtures("controller")
    def test_microscope_and_camera_are_valid(self, tmp_path, controller):
        """Test if microscope and camera are valid objects."""
        self.init_start_program_test(controller, tmp_path)

        # check mircoscope and camera are valid
        assert isinstance(controller.microscope, DummyMicroscope)
        assert isinstance(controller.camera, DummyCamera)
    
    @pytest.mark.usefixtures("controller")
    def test_show_create_measurement_is_executed(self, tmp_path, controller):
        """Test whether the view is instructed to show the create measurement 
        view."""
        self.init_start_program_test(controller, tmp_path)

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
    def test_measurement_is_valid(self, tmp_path, controller):
        """Test whether a valid measurement object is received (the measurement
        object creation function is tested in test_measurement.py)."""
        self.init_start_program_test(controller, tmp_path)

        # shown exactly one time
        assert isinstance(controller.measurement, pylo.Measurement)
    
    @pytest.mark.usefixtures("controller")
    def test_series_ready_after_measurement_is_created(self, tmp_path, controller):
        """Test if the series_ready event is fired after the measurement is 
        ready."""
        
        self.init_start_program_test(controller, tmp_path)

        # contains the request with group at index 0 and key at index 1
        requests = [r[:2] for r in controller.configuration.request_log]
        index = requests.index(("measurement", "save-directory"))
        measurement_time = controller.configuration.request_log[index][2]

        # shown exactly one time
        assert measurement_time <= self.series_ready_times[0]

    def microscope_ready_handler(self):
        """The handler for the microscope_ready event."""
        self.microscope_ready_times.append(time.time())

    def before_record_handler(self):
        """The handler for the before_record event."""
        self.before_record_times.append(time.time())

    def after_record_handler(self):
        """The handler for the after_record event."""
        self.after_record_times.append(time.time())

    def measurement_ready_handler(self):
        """The handler for the measurement_ready event."""
        self.measurement_ready_times.append(time.time())
    
    @pytest.mark.usefixtures("controller")
    def test_by_event_measurement_is_started(self, tmp_path, controller):
        """Test if the measuremnet fires the events which means it has started."""
        
        # clear events
        pylo.microscope_ready.clear()
        pylo.before_record.clear()
        pylo.after_record.clear()
        pylo.measurement_ready.clear()

        # clear time logs
        self.microscope_ready_times = []
        self.before_record_times = []
        self.after_record_times = []
        self.measurement_ready_times = []

        # bind handler
        pylo.microscope_ready.append(self.microscope_ready_handler)
        pylo.before_record.append(self.before_record_handler)
        pylo.after_record.append(self.after_record_handler)
        pylo.measurement_ready.append(self.measurement_ready_handler)

        self.init_start_program_test(controller, tmp_path)

        # contains the request with group at index 0 and key at index 1
        requests = [r[:2] for r in controller.configuration.request_log]
        index = requests.index(("measurement", "save-directory"))
        measurement_time = controller.configuration.request_log[index][2]

        # events are fired
        assert len(self.microscope_ready_times) == 1
        assert len(self.before_record_times) >= 1
        assert len(self.after_record_times) >= 1
        assert len(self.measurement_ready_times) == 1

        # events are fired after the measurement is created
        assert measurement_time <= min(self.microscope_ready_times)
        assert measurement_time <= min(self.before_record_times)
        assert measurement_time <= min(self.after_record_times)
        assert measurement_time <= min(self.measurement_ready_times)
    
    @pytest.mark.usefixtures("controller")
    def test_by_files_measurement_is_started(self, tmp_path, controller):
        """Test if the measuremnet creates at least one file."""

        self.init_start_program_test(controller, tmp_path)

        files = os.listdir(str(tmp_path))

        assert len(files) > 0

        for f in files:
            mtime = os.path.getmtime(os.path.join(str(tmp_path), f))

            assert (self.start_time < mtime or 
                    math.isclose(self.start_time, mtime))
            assert (max(self.before_init_times) < mtime or 
                    math.isclose(max(self.before_init_times), mtime))
            assert (max(self.init_ready_times) < mtime or 
                    math.isclose(max(self.init_ready_times), mtime))
            assert (max(self.user_ready_times) < mtime or 
                    math.isclose(max(self.user_ready_times), mtime))
    
    @pytest.mark.usefixtures("controller")
    def test_error_shown_microscope_module_wrong(self, tmp_path, controller):
        """Test if an error is shown when the microsocpe could not be loaded."""

        controller.configuration.setValue("setup", "microscope-module", "nontexistingmodule")
        controller.configuration.setValue("setup", "microscope-class", "DummyMicroscope")

        with pytest.raises(DummyViewShowsError):
            # DummyView raises DummyViewShowsError when showError() is called
            self.init_start_program_test(controller, tmp_path, change_microscope=False)

        found = False
        for e in controller.view.error_log:
            if "The microscope or the camera module could not be found" in str(e[0]):
                found = True
                break
        
        assert found
    
    @pytest.mark.usefixtures("controller")
    def test_error_shown_microscope_class_wrong(self, tmp_path, controller):
        """Test if an error is shown when the microsocpe could not be loaded."""

        controller.configuration.setValue("setup", "microscope-module", "test_controller.py")
        controller.configuration.setValue("setup", "microscope-class", "NonExistingClass")
        with pytest.raises(DummyViewShowsError):
            # DummyView raises DummyViewShowsError when showError() is called
            self.init_start_program_test(controller, tmp_path, change_microscope=False)

        found = False
        for e in controller.view.error_log:
            if "the given class either does not exist or is not a class" in str(e[0]):
                found = True
                break
        
        assert found
    
    @pytest.mark.usefixtures("controller")
    def test_error_shown_camera_module_wrong(self, tmp_path, controller):
        """Test if an error is shown when the microsocpe could not be loaded."""

        controller.configuration.setValue("setup", "camera-module", "nontexistingmodule")
        controller.configuration.setValue("setup", "camera-class", "DummyCamera")
        with pytest.raises(DummyViewShowsError):
            # DummyView raises DummyViewShowsError when showError() is called
            self.init_start_program_test(controller, tmp_path, change_camera=False)

        found = False
        for e in controller.view.error_log:
            if "The microscope or the camera module could not be found" in str(e[0]):
                found = True
                break
        
        assert found
    
    @pytest.mark.usefixtures("controller")
    def test_error_shown_camera_class_wrong(self, tmp_path, controller):
        """Test if an error is shown when the camera could not be loaded."""

        controller.configuration.setValue("setup", "camera-module", "test_controller.py")
        controller.configuration.setValue("setup", "camera-class", "NonExistingClass")
        with pytest.raises(DummyViewShowsError):
            # DummyView raises DummyViewShowsError when showError() is called
            self.init_start_program_test(controller, tmp_path, change_camera=False)

        found = False
        for e in controller.view.error_log:
            if "the given class either does not exist or is not a class" in str(e[0]):
                found = True
                break
        
        assert found
    
    @pytest.mark.usefixtures("controller")
    def test_error_shown_create_measurement_wrong_return_type(self, tmp_path, controller):
        """Test if an error is shown when the view returns a wrong type from 
        the showCreateMeasurement() function."""
        
        controller.view.measurement_to_create = False
        with pytest.raises(DummyViewShowsError):
            # DummyView raises DummyViewShowsError when showError() is called
            self.init_start_program_test(controller, tmp_path)

        found = False
        for e in controller.view.error_log:
            if "The view returned an invalid measurement" in str(e[0]):
                found = True
                break
        
        assert found
    
    @pytest.mark.usefixtures("controller")
    def test_error_shown_create_measurement_incomplete1(self, tmp_path, controller):
        """Test if an error is shown when the view returns an incomplete 
        measurement layout."""
        
        # do not give a start setup
        controller.view.measurement_to_create = (
            {},
            {"variable": "notexisting", "start": 0, "end": 1, "step-width": 1}
        )
        with pytest.raises(DummyViewShowsError):
            # DummyView raises DummyViewShowsError when showError() is called
            self.init_start_program_test(controller, tmp_path)

        found = False
        for e in controller.view.error_log:
            if "The measurement could not be initialized" in str(e[0]):
                found = True
                break
        
        assert found
    
    @pytest.mark.usefixtures("controller")
    def test_error_shown_create_measurement_incomplete2(self, tmp_path, controller):
        """Test if an error is shown when the view returns an incomplete 
        measurement layout."""
        
        # do not give a start setup
        controller.view.measurement_to_create = (
            {"measurement-var": 0},
            {}
        )
        with pytest.raises(DummyViewShowsError):
            # DummyView raises DummyViewShowsError when showError() is called
            self.init_start_program_test(controller, tmp_path)

        found = False
        for e in controller.view.error_log:
            if "The measurement could not be initialized" in str(e[0]):
                found = True
                break
        
        assert found
    
    @pytest.mark.usefixtures("controller")
    def test_error_shown_create_measurement_incomplete3(self, tmp_path, controller):
        """Test if an error is shown when the view returns an incomplete 
        measurement layout."""
        
        # do not give a start setup
        controller.view.measurement_to_create = (
            {},
            {}
        )
        with pytest.raises(DummyViewShowsError):
            # DummyView raises DummyViewShowsError when showError() is called
            self.init_start_program_test(controller, tmp_path)

        found = False
        for e in controller.view.error_log:
            if "The measurement could not be initialized" in str(e[0]):
                found = True
                break
        
        assert found
    
    def raise_test_exception(self):
        """Raise an exception"""
        raise Exception("TestController: Test exception")
    
    @pytest.mark.usefixtures("controller")
    def test_error_when_exception_in_controller_event(self, tmp_path, controller):
        """Test if an error is shown when there is an exception raised in the 
        controller event."""

        with pytest.raises(DummyViewShowsError):
            # DummyView raises DummyViewShowsError when showError() is called
            self.init_start_program_test(
                controller, 
                tmp_path, 
                before_start=lambda: pylo.init_ready.append(self.raise_test_exception)
            )

        found = False
        for e in controller.view.error_log:
            if "Test exception" in str(e[0]):
                found = True
                break
        
        assert found
    
    @pytest.mark.usefixtures("controller")
    def test_error_when_exception_in_measurement_event(self, tmp_path, controller):
        """Test if an error is shown when there is an exception raised in the 
        measurement event."""
        
        with pytest.raises(DummyViewShowsError):
            # DummyView raises DummyViewShowsError when showError() is called
            self.init_start_program_test(
                controller, 
                tmp_path, 
                before_start=lambda: pylo.after_record.append(self.raise_test_exception)
            )

        found = False
        for e in controller.view.error_log:
            if "Test exception" in str(e[0]):
                found = True
                break
        
        assert found
    
    @pytest.mark.usefixtures("controller")
    @pytest.mark.parametrize("group,key,for_camera", [
        ("setup", "microscope-module", False),
        ("setup", "microscope-class", False),
        ("setup", "camera-module", True),
        ("setup", "camera-class", True),
    ])
    def test_stop_program_exception_stops_in_ask_for_microscope_or_camera(self, tmp_path, controller, group, key, for_camera):
        """Test if the program is stopped if the view raises the StopProgram
        Exception while it is aksing for the micrsocope or camera. This is 
        equal to the user clicking the cancel button."""

        controller.view.ask_for_response.append(
            ((group, key), self.raise_stop_program)
        )

        controller.configuration.removeElement(group, key)
        
        self.init_start_program_test(
            controller, 
            tmp_path, 
            change_microscope=for_camera, 
            change_camera=False
        )

        assert len(self.before_init_times) == 1
        assert len(self.init_ready_times) == 0
        assert len(self.user_ready_times) == 0
        assert len(self.series_ready_times) == 0

        # assert (isinstance(controller.microscope, pylo.microscopes.MicroscopeInterface) == 
        #         for_camera)
        assert not isinstance(controller.camera, pylo.cameras.CameraInterface)
        assert not isinstance(controller.measurement, pylo.Measurement)
    
    @pytest.mark.usefixtures("controller")
    def test_stop_program_exception_stops_in_ask_for_measurement(self, tmp_path, controller):
        """Test if the program is stopped if the view raises the StopProgram
        Exception while it is aksing for the measurement. This is 
        equal to the user clicking the cancel button."""

        controller.view.measurement_to_create = self.raise_stop_program
        
        self.init_start_program_test(controller, tmp_path)

        assert len(self.before_init_times) == 1
        assert len(self.init_ready_times) == 1
        assert len(self.user_ready_times) == 0
        assert len(self.series_ready_times) == 0

        assert isinstance(controller.microscope, pylo.microscopes.MicroscopeInterface)
        assert isinstance(controller.camera, pylo.cameras.CameraInterface)
        assert not isinstance(controller.measurement, pylo.Measurement)
    
    @pytest.mark.usefixtures("controller")
    def test_stop_program_stops_current_measurement(self, tmp_path, controller):
        """Test if the program is stopped if the view raises the StopProgram
        Exception while it is aksing for the measurement. This is 
        equal to the user clicking the cancel button."""

        controller.view.measurement_to_create = self.raise_stop_program
        
        self.init_start_program_test(controller, tmp_path)

        assert len(self.before_init_times) == 1
        assert len(self.init_ready_times) == 1
        assert len(self.user_ready_times) == 0
        assert len(self.series_ready_times) == 0

        assert isinstance(controller.microscope, pylo.microscopes.MicroscopeInterface)
        assert isinstance(controller.camera, pylo.cameras.CameraInterface)
        assert not isinstance(controller.measurement, pylo.Measurement)
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("controller")
    def test_stop_program_loop_stops_program_while_working(self, tmp_path, controller):
        """Test if the program loop is stoppend when calling 
        Controller::stopProgramLoop() in another thread."""

        global measurement_duration_time

        # add a listener to the microscope_ready event
        pylo.microscope_ready.clear()
        pylo.measurement_ready.clear()

        self.microscope_ready_times = []
        self.measurement_ready_times = []

        pylo.microscope_ready.append(self.microscope_ready_handler)
        pylo.measurement_ready.append(self.measurement_ready_handler)

        # let the microscope take one second to arrange the measuremnet 
        # variable
        measurement_duration_time = 1
        
        # program is running
        self.init_start_program_test(controller, tmp_path, wait_for_finish=False)
        
        # wait some time until the measurement should be started
        time.sleep(measurement_duration_time * 2 / 3)

        # stop the program
        controller.stopProgramLoop()
        controller.waitForProgram()
        end_time = time.time()

        # there should not pass that much time until the program is eded
        assert self.start_time + measurement_duration_time <= end_time

        # make sure the test is correct, the measurement has started
        assert len(self.before_init_times) == 1
        assert len(self.init_ready_times) == 1
        assert len(self.user_ready_times) == 1
        assert len(self.series_ready_times) == 1
        assert len(self.microscope_ready_times) == 1

        # make sure the measurement has not finised
        assert len(self.measurement_ready_times) == 0
    
    @pytest.mark.slow()
    @pytest.mark.usefixtures("controller")
    def test_restart_program_loop_works_program_while_working(self, tmp_path, controller):
        """Test if the program loop is stoppend when calling 
        Controller::restartProgramLoop() in another thread."""

        global measurement_duration_time

        # add a listener to the microscope_ready event
        pylo.microscope_ready.clear()
        pylo.measurement_ready.clear()

        self.microscope_ready_times = []
        self.measurement_ready_times = []

        pylo.microscope_ready.append(self.microscope_ready_handler)
        pylo.measurement_ready.append(self.measurement_ready_handler)

        # let the microscope take one second to arrange the measuremnet 
        # variable
        measurement_duration_time = 1
        
        # program is running
        self.init_start_program_test(controller, tmp_path, wait_for_finish=False)
        
        # wait some time until the measurement should be started
        time.sleep(measurement_duration_time * 2 / 3)

        # stop the program
        restart_time = time.time()
        controller.restartProgramLoop()
        controller.waitForProgram()
        end_time = time.time()

        assert self.start_time < restart_time
        assert restart_time < end_time
        
        # contains the request with group at index 0 and key at index 1
        requests = []
        request_times_dict = {}
        for group, key, t in controller.configuration.request_log:
            requests.append((group, key))

            k = "{}-{}".format(group, key)
            if not k in request_times_dict:
                request_times_dict[k] = []
            
            request_times_dict[k].append(t)

        # all the events must be triggered twice because the program runs twice
        assert len(self.before_init_times) == 2
        assert len(self.init_ready_times) == 2
        assert len(self.user_ready_times) == 2
        assert len(self.series_ready_times) == 2
        assert len(self.microscope_ready_times) == 2

        # showCreateMeasurement() is shown twice
        assert len(controller.view.shown_create_measurement_times) == 2

        # check if mircoscope and camera are created ONCE, answers are saved
        # in the configuration
        assert requests.count(("setup", "microscope-module")) == 1
        assert requests.count(("setup", "microscope-class")) == 1
        assert requests.count(("setup", "camera-module")) == 1
        assert requests.count(("setup", "camera-class")) == 1

        # all first events are triggered before the restart
        assert self.before_init_times[0] <= restart_time
        assert self.init_ready_times[0] <= restart_time
        assert self.user_ready_times[0] <= restart_time
        assert self.microscope_ready_times[0] <= restart_time

        # all first requests are made before the restart
        assert min(request_times_dict["setup-microscope-module"]) <= restart_time
        assert min(request_times_dict["setup-microscope-class"]) <= restart_time
        assert min(request_times_dict["setup-camera-module"]) <= restart_time
        assert min(request_times_dict["setup-camera-class"]) <= restart_time

        # all second events are triggered after the restart
        assert restart_time <= self.before_init_times[1]
        assert restart_time <= self.init_ready_times[1]
        assert restart_time <= self.user_ready_times[1]
        assert restart_time <= self.microscope_ready_times[1]

        # the measurement finishes only one time
        assert len(self.measurement_ready_times) == 1