import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
import pytest

import pylo

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
