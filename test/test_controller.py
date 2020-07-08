import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
import pytest

import pylo

pylo_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pylo")

# class DummyView(pylo.AbstractView):
class DummyView:
    def __init__(self):
        self.clear()
    
    def clear(self):
        self.ask_for_response = []
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

class DummyConfiguration(pylo.AbstractConfiguration):
    def loadConfiguration(self):
        self.clear()
    
    def clear(self):
        self.configuration = {}

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

@pytest.fixture
def controller():
    pylo.config.CONFIGURATION = DummyConfiguration()
    pylo.config.VIEW = DummyView()
    controller = pylo.Controller()

    controller.view.clear()
    controller.configuration.clear()

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
            if e:
                # check if the value exists
                assert values[i] == controller.configuration.getValue(l["group"], 
                                                                      l["key"])
            else:
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
    
    def remove_file_and_dir(self, file_name):
        """Removes the given file and the parent directory if the directory
        only contained this file."""

        parent_dir = os.path.dirname(file_name)
        os.remove(file_name)

        if len(os.listdir(parent_dir)) == 0:
            os.removedirs(parent_dir)
    
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
        
        self.remove_file_and_dir(path)
    
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
        
        self.remove_file_and_dir(path)
    
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
        
        self.remove_file_and_dir(path)

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
        
        self.remove_file_and_dir(path)

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
        
        self.remove_file_and_dir(path)

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

        self.remove_file_and_dir(path)
        
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

        self.remove_file_and_dir(path)
        
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

        self.remove_file_and_dir(path)
