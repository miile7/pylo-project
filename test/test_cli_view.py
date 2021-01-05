import os
import sys

if __name__ == "__main__":
    # For direct call only
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class DummyOut:
    def __init__(self):
        self.io_log = ""
        self.out_buffer = ""
        self.input_response = ""
        self.max_write_count = 500
        self.cls()

    def write(self, text):
        self.write_counter += 1
        if self.write_counter > self.max_write_count:
            realprint(self.io_log)
            raise RecursionError("Too many calls of write().")
        self.out_buffer += text
        # fix backspace character deleting other characters, allow to remove
        # old content
        while "\b" in self.out_buffer:
            i = self.out_buffer.index("\b")
            if i > 0:
                self.out_buffer = self.out_buffer[:i-1] + self.out_buffer[i + 1:]
            else:
                self.out_buffer = self.out_buffer[1:]
        self.io_log += text
    
    def flush(self):
        pass
    
    def read(self):
        self.read_counter += 1
        if self.read_counter > self.max_write_count:
            realprint(self.io_log)
            raise RecursionError("Too many calls of read().")
        
        if callable(self.input_response):
            r = self.input_response()
        else:
            r = self.input_response
        
        self.io_log += " < input: '" + str(r) + "'\n"
        
        return r
    
    def readline(self):
        return str(self.read()) + "\n"
    
    def cls(self):
        self.io_log = ""
        self.read_counter = 0
        self.write_counter = 0
        self.out_buffer = ""

writer = DummyOut()

real_std_out = sys.stdout
def realprint(*values, sep=" ", end="\n"):
    global real_std_out
    print(sep.join(map(str, values)) + end, file=real_std_out)

import re
import string
import pytest
import random

import pylo

class DummyView(pylo.AbstractView):
    def showCreateMeasurement(self, *args, **kwargs):
        pass

    def showSettings(self, *args, **kwargs):
        pass

    def showHint(self, *args, **kwargs):
        realprint(args, kwargs)

    def showError(self, *args, **kwargs):
        realprint(args, kwargs)

    def print(self, *args, **kwargs):
        realprint(args, kwargs)

    def showRunning(self, *args, **kwargs):
        pass

    def askFor(self, *args):
        return ["ASK_FOR_DEFAULT_OUTPUT"] * len(args)

class DummyMicroscope(pylo.MicroscopeInterface):
    def __init__(self):
        self.supported_measurement_variables = [
            pylo.MeasurementVariable("focus", "Focus", 0, 0xfa,
                            format=pylo.Datatype.hex_int),
            pylo.MeasurementVariable("magnetic-field", "Magnetic Field", 0, 5),
            pylo.MeasurementVariable("tilt", "Tilt", -5, 5, calibration=5),
        ]
        self.supports_parallel_measurement_variable_setting = False
        self.values = {}

    def setInLorentzMode(self, lorentz_mode):
        pass

    def getInLorentzMode(self):
        return True
    
    def setMeasurementVariableValue(self, id_, value):
        self.values[id_] = value
    
    def getMeasurementVariableValue(self, id_):
        try:
            return self.values[id_]
        except KeyError:
            return None
        
    def resetToSafeState(self):
        realprint("Resetting to safe state")
        assert False
    
reg = re.compile(r"\s+")
def get_compare_text(text):
    """Get the text with all whitespace replaced to only one space.
    
    Parameters
    ----------
    text : str
        The text
        
    Returns
    -------
    str
        The `text` where all whitespace is replaced with one space
    """
    global reg
    return " ".join(reg.split(text))

@pytest.fixture()
def cliview():
    global writer

    writer.cls()
    sys.stdout = writer
    sys.stdin = writer

    yield pylo.CLIView()

    sys.stdout = sys.__stdout__
    sys.stdin = sys.__stdin__

@pytest.fixture()
def controller():
    controller = pylo.Controller(DummyView(), pylo.AbstractConfiguration())
    controller.microscope = DummyMicroscope()

    return controller

@pytest.fixture()
def configuration():
    configuration = pylo.AbstractConfiguration()

    configuration.addConfigurationOption("options", "key1", datatype=int, 
        description="Input the value for the first test configuration value.")
    configuration.addConfigurationOption("options", "key2", datatype=float,
        default_value=1.0
    )
    configuration.setValue("already-set", "key3", "This value is set", 
        datatype=str
    )

    return configuration

# input_definition, user_input, expected value
default_valid_select_definition = [
    # string
    ({"label": "Label a", "id": "testid1", "datatype": str, "value": "", 
        "required": True}, "testinput", "testinput"),
    # int
    ({"label": "Label b", "id": "testid2", "datatype": int, "value": 5, 
        "required": True, "min_value": 2, "max_value": 10}, "10", 10),
    ({"label": "Label c", "id": "testid3", "datatype": int, "value": 5, 
        "required": True, "min_value": 2, "max_value": 10}, "2", 2),
    # float
    ({"label": "Label d", "id": "testid4", "datatype": float, "value": 0, 
        "required": True, "min_value": -1.25, "max_value": 1.25}, "-1.25", -1.25),
    ({"label": "Label e", "id": "testid5", "datatype": float, "value": 0, 
        "required": True, "min_value": -1.25, "max_value": 1.25}, "1.25", 1.25),
    # min *or* max, not both
    ({"label": "Label f", "id": "testid6", "datatype": int, "value": 2, 
        "required": True, "min_value": -10}, "-10", -10),
    ({"label": "Label g", "id": "testid7", "datatype": float, "value": -22, 
        "required": True, "max_value": -10}, "-10", -10.0),
    # all boolean possibilites
    ({"label": "Label h", "id": "testid8", "datatype": bool, "value": True, 
        "required": True}, "tRuE", True),
    ({"label": "Label i", "id": "testid9", "datatype": bool, "value": False, 
        "required": True}, "t", True),
    ({"label": "Label j", "id": "testid10", "datatype": bool, "value": False, 
        "required": True}, "yes", True),
    ({"label": "Label k", "id": "testid11", "datatype": bool, "value": False, 
        "required": True}, "y", True),
    ({"label": "Label l", "id": "testid12", "datatype": bool, "value": False, 
        "required": True}, "on", True),
    ({"label": "Label m", "id": "testid13", "datatype": bool, "value": True, 
        "required": True}, "fAlSe", False),
    ({"label": "Label n", "id": "testid14", "datatype": bool, "value": True, 
        "required": True}, "f", False),
    ({"label": "Label o", "id": "testid15", "datatype": bool, "value": True, 
        "required": True}, "no", False),
    ({"label": "Label p", "id": "testid16", "datatype": bool, "value": True, 
        "required": True}, "n", False),
    ({"label": "Label q", "id": "testid17", "datatype": bool, "value": True, 
        "required": True}, "off", False),
    # possibility list
    ({"label": "Label r", "id": "testid18", "datatype": pylo.Datatype.options(["d", "b"]), 
        "value": "d", "required": True}, "b", "b"),
    ({"label": "Label s", "id": "testid19", "datatype": pylo.Datatype.options(["d", "b"]), 
        "value": "d", "required": True}, "B", "b"),
    # abort command and empty commands are possibilities
    ({"label": "Label t", "id": "testid20", "datatype": pylo.Datatype.options(["a", "x"]), 
        "value": "a", "required": True}, "a", "a"),
    ({"label": "Label u", "id": "testid21", "datatype": pylo.Datatype.options(["a", "x"]), 
        "value": "a", "required": True}, "x", "x")
]

class TestCLIView:
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("text", [
        "Short test text",
        "This is a longer test text. This text should be broken at one of the " + 
        "spaces but not inside a word. This also should at least be two lines " +
        "maybe even three or more."
    ])
    def test_print(self, cliview, text):
        """Test if the print function works."""
        global writer

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        cliview.print(text)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        # check if texts are equal, note that the title is also in the printed
        # in the buffer
        assert get_compare_text(text) in get_compare_text(writer.out_buffer)
        
        # check if each line is less than the maxlen
        for line in writer.out_buffer.split("\n"):
            assert len(line) <= cliview.line_length
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("text,user_input", [
        ("Short test text", "Test"),
        ("This is a longer test text. This text should be broken at one of the " + 
         "spaces but not inside a word. This also should at least be two lines " +
         "maybe even three or more.", 5)
    ])
    def test_input(self, cliview, text, user_input):
        """Test if the print function works."""
        global writer

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = user_input
        inp = cliview.input(text)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        # check if texts are equal, note that the title is also in the printed
        # in the buffer
        assert get_compare_text(text) in get_compare_text(writer.out_buffer)
        
        # check if each line is less than the maxlen
        for line in writer.out_buffer.split("\n"):
            assert len(line) <= cliview.line_length
        
        # check if the input is correct
        assert inp == str(user_input)
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("input_definition,user_input,expected", 
        default_valid_select_definition + [
        # testing optional values
        ({"label": "Label v", "id": "testid22", "datatype": str, "value": "", 
            "required": False}, "!empty", None),
        ({"label": "Label w", "id": "testid23", "datatype": int, "value": 5, 
            "required": False}, "x", None),
        # not required by default
        ({"label": "Label x", "id": "testid24", "datatype": float, "value": 5.5}, 
            "x", None),
        ({"label": "Label y", "id": "testid25", "datatype": bool, "value": False}, 
            "x", None),
        ({"label": "Label z", "id": "testid26", "datatype": pylo.Datatype.options(["d", "b"]), "value": "d"}, 
            "x", None)
    ])
    def test_input_value_loop_valid_values(self, cliview, input_definition, user_input, expected):
        """Test if the _inputValueLoop() function with valid user inputs."""
        global writer

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = user_input
        inp = cliview._inputValueLoop(input_definition)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        out = writer.out_buffer

        # check if label is shown
        assert input_definition["label"] in get_compare_text(out)

        # check if limits are displayed
        if "min_value" in input_definition:
            assert str(input_definition["min_value"]) in out
        if "max_value" in input_definition:
            assert str(input_definition["max_value"]) in out

        # check required
        assert (inp is not None or not "required" in input_definition or 
                not input_definition["required"])
        
        # check returned value
        if not inp is None:
            if isinstance(input_definition["datatype"], pylo.OptionDatatype):
                assert inp in input_definition["datatype"].options
            else:
                assert type(inp) == input_definition["datatype"]
        
        assert type(inp) == type(expected)
        assert inp == expected
    
    def response_callback(self):
        """The callback for the user input response."""
        global writer
        self.response_counter += 1
        self.out_buffers.append(writer.out_buffer)
        return self.response_answers[(self.response_counter - 1) % len(self.response_answers)]
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("input_definition,user_input1,user_input2,expected", [
        # wrong types
        ({"label": "Testinput", "id": "testid27", "datatype": int, "value": 5, 
          "required": True, "min_value": 2, "max_value": 10}, "invalid", "10", 10),
        ({"label": "Testinput", "id": "testid28", "datatype": float, "value": 5, 
          "required": True, "min_value": -38939.232, "max_value": 1}, "invalid", "-323.25", -323.25),
        ({"label": "Testinput", "id": "testid29", "datatype": bool, "value": True, 
          "required": True}, "ney", "no", False),
        ({"label": "Testinput", "id": "testid30", "datatype": bool, "value": False, 
          "required": True}, "yep", "yes", True),
        # not in boundaries
        ({"label": "Testinput", "id": "testid31", "datatype": int, "value": 5, 
          "required": True, "min_value": 2, "max_value": 10}, "1", "2", 2),
        ({"label": "Testinput", "id": "testid32", "datatype": int, "value": 4, 
          "required": True, "min_value": 2, "max_value": 10}, "22", "5", 5),
        ({"label": "Testinput", "id": "testid33", "datatype": float, "value": 0, 
          "required": True, "min_value": -1.25, "max_value": 1.25}, "-1.26", "-1.25", -1.25),
        ({"label": "Testinput", "id": "testid34", "datatype": float, "value": 0, 
          "required": True, "min_value": -1.25, "max_value": 1.25}, "1.26", "1.125", 1.125),
        ({"label": "Testinput", "id": "testid35", "datatype": int, "value": 2, 
          "required": True, "min_value": -10}, "-33", "99999", 99999),
        ({"label": "Testinput", "id": "testid36", "datatype": float, "value": -22, 
          "required": True, "max_value": -10}, "-6.4334", "-10", -10.0),
        # not in possibilities
        ({"label": "Testinput", "id": "testid37", "datatype": pylo.Datatype.options(["d", "b"]), "value": "d", 
          "required": True}, "w", "b", "b")
    ])
    def test_input_value_loop_invalid_values(self, cliview, input_definition, user_input1, user_input2, expected):
        """Test if the _inputValueLoop() function with invalid user inputs."""
        global writer

        num_wrong_answers = random.randint(1, 4)
        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = [user_input1] * num_wrong_answers + [user_input2]

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = self.response_callback
        inp = cliview._inputValueLoop(input_definition)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__
        
        # check if asked the correct amount of times
        assert self.response_counter == num_wrong_answers + 1

        # check returned value
        if isinstance(input_definition["datatype"], pylo.OptionDatatype):
            assert inp in input_definition["datatype"].options
        else:
            assert type(inp) == input_definition["datatype"]
        
        assert type(inp) == type(expected)
        assert inp == expected
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("input_definition,user_input", [
        ({"label": "Testinput", "id": "testid38", "datatype": str, "value": "a", 
          "required": True}, "!abort"),
        ({"label": "Testinput", "id": "testid39", "datatype": int, "value": 5, 
          "min_value": 2, "max_value": 10}, "a"),
        ({"label": "Testinput", "id": "testid40", "datatype": bool, "value": False}, 
          "a"),
        ({"label": "Testinput", "id": "testid41", "datatype": pylo.Datatype.options(["x", "a"]), 
          "value": "x"}, "!abort"),
        ({"label": "Testinput", "id": "testid42", "datatype": pylo.Datatype.options(["x", "a", "!abort"]), 
          "value": "x"}, "!a"),
    ])
    def test_input_value_loop_abort(self, cliview, input_definition, user_input):
        """Test if aborting works in the _inputValueLoop() function"""
        global writer

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = user_input

        with pytest.raises(pylo.StopProgram):
            cliview._inputValueLoop(input_definition)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("input_definition,user_input1,user_input2,expected", [
        ({"label": "Testinput", "id": "testid43", "datatype": int, "value": 5, 
          "required": True, "min_value": 2, "max_value": 10}, "x", "10", 10),
        ({"label": "Testinput", "id": "testid44", "datatype": float, "value": 5, 
          "required": True, "min_value": -38939.232, "max_value": 1}, "x", 
          "-323.25", -323.25),
        ({"label": "Testinput", "id": "testid45", "datatype": pylo.Datatype.options(["a", "b"]), "value": "a", 
          "required": True}, "x", "b", "b"),
        ({"label": "Testinput", "id": "testid46", "datatype": pylo.Datatype.options(["x", "c"]), "value": "x", 
          "required": True}, "!empty", "c", "c"),
        ({"label": "Testinput", "id": "testid47", "datatype": pylo.Datatype.options(["x", "c", "!empty"]), 
          "value": "x", "required": True}, "!a", "c", "c")
    ])
    def test_input_value_loop_missing_required_values(self, cliview, input_definition, user_input1, user_input2, expected):
        """Test if the _inputValueLoop() does not allow to empty required 
        values."""
        global writer

        num_abort_tries = random.randint(1, 4)
        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = [user_input1] * num_abort_tries + [user_input2]

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = self.response_callback
        inp = cliview._inputValueLoop(input_definition)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__
        
        # check if asked the correct amount of times
        assert self.response_counter == num_abort_tries + 1

        # check if an error was shown
        for i in range(1, self.response_counter):
            o = get_compare_text(self.out_buffers[i])
            assert "is required" in o
            assert "have to" in o
            assert "put in" in o

        # check returned value
        if isinstance(input_definition["datatype"], pylo.OptionDatatype):
            assert inp in input_definition["datatype"].options
        else:
            assert type(inp) == input_definition["datatype"]
        
        assert type(inp) == type(expected)
        assert inp == expected
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("select_definition", ([d[0] for d in default_valid_select_definition], ))
    def test_print_select_output(self, cliview, select_definition):
        """Test the print select output."""
        global writer

        # add some random texts to the select overview
        texts = []
        letters = string.ascii_lowercase
        word = lambda: ''.join(random.choice(letters) for _ in range(random.randint(3, 20)))
        for _ in range(0, random.randint(1, 3)):
            text = " ".join([word() for _ in range(random.randint(3, 20))])
            texts.append(text)
            select_definition.insert(
                random.randint(0, len(select_definition) - 1),
                text
            )

        self.response_counter = 0
        self.out_buffers = []
        # confirm
        self.response_answers = ["c"]

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = self.response_callback
        cliview._printSelect(*select_definition)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        # check if the overview is correctly built, that means that the order 
        # is represented in the lines in the output
        out = writer.out_buffer.split("\n")
        last_index = -1
        for input_definition in select_definition:
            following_out = out[last_index+1:]
            following_text = get_compare_text("\n".join(following_out))

            if isinstance(input_definition, str):
                # check if the text comes after the last input_definition
                assert input_definition in following_text
                last_word = input_definition.split(" ")[-1]
            else:
                found = False
                for i, line in enumerate(following_out):
                    # check if the label is given, check if the label string
                    # is part of the line string, 'label' in following_out does
                    # not work because that looks for an equal item in the list
                    if input_definition["label"] in line:
                        found = True
                        break
                
                assert found
                last_word = input_definition["label"]
                
            for i, line in enumerate(following_out):
                if last_word in line:
                    last_index = i
                    break
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("select_definition,commands,expected", [
        # continue
        ([d[0] for d in default_valid_select_definition], ("c", ), True),
        # quit
        ([d[0] for d in default_valid_select_definition], ("q", ), False),
        # set any value
        ([d[0] for d in default_valid_select_definition], ("0", "random text"), None),
        # set any value, then abort
        ([d[0] for d in default_valid_select_definition], ("0", "c"), None),
    ])
    def test_print_select_command_returns(self, cliview, select_definition, commands, expected):
        """Test the print select output."""
        global writer

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = commands

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = self.response_callback
        values, command_return, changed = cliview._printSelect(*select_definition)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        assert command_return == expected
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("select_definition,user_inputs,expected_id,expected", [
        (
            # eery time all select_definitions
            [d[0] for d in default_valid_select_definition],
            # create test for each value to set and check
            (i, x[1]), x[0]["id"], x[2]
        ) for i, x in enumerate(default_valid_select_definition)
    ])
    def test_print_select_change_value(self, cliview, select_definition, user_inputs, expected_id, expected):
        """Test changing a value to a valid value (invalid values are not 
        allowed because of _inputValueLoop())."""
        global writer

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = user_inputs

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = self.response_callback
        values, command_return, change = cliview._printSelect(*select_definition)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        expected_values = dict(zip(
            [d["id"] for d in select_definition],
            [d["value"] for d in select_definition]
        ))
        expected_values[expected_id] = expected

        assert change == expected_id
        assert command_return == None
        assert values == expected_values
    
    @pytest.mark.usefixtures("cliview", "controller")
    @pytest.mark.parametrize("series,depth,expecting_errors", [
        # values are missing
        ({"variable": "focus"}, 1, False),
        # values are wrong
        ({"variable": "focus", "start": -1}, 1, True),
        ({"variable": "focus", "end": 0x100}, 1, True),
        # values are missing in child
        ({"variable": "focus", "start": 0, "end": 5, "step-width": 1, 
          "on-each-point": {"variable": "magnetic-field"}}, 2, False),
        # values are wrong in child
        ({"variable": "focus", "start": 0, "end": 5, "step-width": 1, 
          "on-each-point": {"variable": "magnetic-field", "start": -1}}, 2, True),
        ({"variable": "focus", "start": 0, "end": 5, "step-width": 1, 
          "on-each-point": {"variable": "magnetic-field", "end": 6}}, 2, True),
        # invalid on-each-point variable: focus series over focus series
        ({"variable": "focus", "start": 0, "end": 5, "step-width": 1, 
          "on-each-point": {"variable": "focus"}}, 1, True),
    ])
    def test_parse_valid_series_input(self, cliview, controller, series, depth, expecting_errors):
        """Test if the _parseSeriesInputs() function returns the correct 
        inputs and can deal with easy to correct values."""
        
        inputs, messages = cliview._parseSeriesInputs(controller, series)
        
        expected_keys = ("variable", "start", "end", "step-width", "on-each-point")

        realprint(inputs)
        assert len(inputs) == len(expected_keys) * depth

        if expecting_errors:
            assert len(messages) > 0

        # contains the series depth index as the key, series definition as the 
        # value
        measurement_variable_map = {}

        # check if all variable ids are there and valid
        for i in range(depth):
            for k in expected_keys:
                found = False

                for input_definition in inputs:
                    if input_definition["id"] == "series-{}-{}".format(i, k):
                        found = True

                        if not i in measurement_variable_map:
                            measurement_variable_map[i] = {}
                        
                        measurement_variable_map[i][k] = input_definition["value"]
                        break
                
                assert found
        
        measurement_variable_ids = [v.unique_id for v in 
                                    controller.microscope.supported_measurement_variables]
                                
        for i, series_definition in measurement_variable_map.items():
            assert series_definition["variable"] in measurement_variable_ids

            v = controller.microscope.getMeasurementVariableById(
                series_definition["variable"]
            )

            assert v.min_value <= series_definition["start"] 
            assert series_definition["start"] <= v.max_value

            assert v.min_value <= series_definition["end"] 
            assert series_definition["end"] <= v.max_value
    
    # PyLo
    # ****
    #
    #
    # Define the start conditions
    # [0] Focus*:                0x0      0x0 <= val <= 0xfa
    # [1] Magnetic Field*:       0        0 <= val <= 5
    # [2] Tilt*:                 0        -25 <= val <= 25
    #
    # Define the series
    # [3] Series variable*:      focus
    # [4] Start value*:          0x0      0x0 <= val <= 0xfa
    # [5] Step width*:           0x19     0x0 <= val <= 0xfa
    # [6] End value*:            0xfa     0x0 <= val <= 0xfa
    # [7] Series on each point:  <empty>
    #
    # Type in the number to change the value of, type [c] for continue and [q] for
    # quit.
    # Number, [c]ontinue or [q]uit:  < input: '0'
    # 
    # Hint: Use realprint(writer.io_log) to see what happens if an error 
    # asserts False
    @pytest.mark.usefixtures("cliview", "controller")
    @pytest.mark.parametrize("start,series,user_inputs,expected_start,expected_series", [
        # create default series, parameter-1
        (None, None, ("c", ), 
         {"focus": 0, "magnetic-field": 0, "tilt": 0},
         # expecting: start=min, end=max, step-width = end-start/10
         {"variable": "focus", "start": 0, "end": 250, "step-width": 25}),
        # change start conditions
        (None, None, (
            "0", "0xf", # focus to 15
            "1", 3, # magnetic field to 3
            "2", 4, # tilt to 4
            "c", 
         ), 
         # tilt is calibrated by 5
         {"focus": 15, "magnetic-field": 3, "tilt": 4/5},
         # expecting: start=min, end=max, step-width = end-start/10
         {"variable": "focus", "start": 0, "end": 250, "step-width": 25}),
        # create magnetic field series, parameter-2
        (None, None, (
            "3", "magnetic-field", # variable
            "5", 0.5, # step width
            "6", 5, # end
            "c" # continue
         ), 
         {"focus": 0, "magnetic-field": 0, "tilt": 0},
         # expecting: start=min, end=max, step-width = end-start/10
         {"variable": "magnetic-field", "start": 0, "end": 5, "step-width": 0.5}),
        # create tilt field series, parameter-3
        (None, {"variable": "tilt"}, (
            "3", "tilt", # variable
            "c"
         ),
         {"focus": 0, "magnetic-field": 0, "tilt": 0},
         # expecting: start=min, end=max, step-width = end-start/10
         {"variable": "tilt", "start": -5.0, "end": 5.0, "step-width": 1.0}),
        # create tilt field series with changed parameters, testing 
        # calibration in on-each-point series (this was a bug), parameter-4
        (None, {"variable": "tilt"}, (
            "3", "focus", # variable
            "4", "0x0", # focus start
            "5", "0x5", # focus step width
            "6", "0xfa", # focus end
            "7", "tilt", # setting on each point
            "9", -10, # tilt start
            "10", 2.5, # tilt step-width
            "11", 10, # tilt end
            "c"
         ),
         {"focus": 0, "magnetic-field": 0, "tilt": 0},
         # expecting: set value divided by calibration factor, machine takes 
         # uncalibrated value
         {"variable": "focus", "start": 0, "end": 0xfa, "step-width": 0x5, "on-each-point": 
            {"variable": "tilt", "start": -10/5, "end": 10/5, "step-width": 2.5/5}}),
        # create magnetic field series from 1 to 2 with 0.5 stepwidth, 
        # parameter-5
        (None, None, (
            "3", "magnetic-field", # vairable
            "4", 1, # start
            "5", 0.5, # step width
            "6", 2, # end
            "c" # continue
         ),
         {"focus": 0, "magnetic-field": 0, "tilt": 0},
         {"variable": "magnetic-field", "start": 1, "end": 2, "step-width": 0.5}),
        # create focus series from 0 to 16 with 2 stepwidth, parameter-6
        (None, None, (
            "4", "0x0", # start
            "5", "0x2", # step width
            "6", "0x10", # end
            "c" # continue
         ),
         {"focus": 0, "magnetic-field": 0, "tilt": 0},
         {"variable": "focus", "start": 0, "end": 16, "step-width": 2}),
        # create tilt series from -5 to 5 with 1 stepwidth, 
        #   on each point: magnetic field series from 0 to 5, stepwidth 0.5
        #       on each point: focus series from 2 to 4, stepwidth 0.25
        # parameter-7
        (None, None, (
            "3", "tilt", # tilt series
            "4", -5, # start
            "5", 1, # step width
            "6", 5, # end
            "7", "magnetic-field", # on each point
                "9", 0, # start
                "10", 0.5, # step width
                "11", 5, # end
                "12", "focus", # on each point
                    "14", "0x2", # start
                    "15", "0x1", # step width
                    "16", "0x4", # end
            "c" # continue
         ),
         {"focus": 0, "magnetic-field": 0, "tilt": 0},
         {"variable": "tilt", "start": -5/5, "end": 5/5, "step-width": 1/5, "on-each-point":
            {"variable": "magnetic-field", "start": 0, "end": 5, "step-width": 0.5, 
             "on-each-point":
                {"variable": "focus", "start": 0x2, "end": 0x4, "step-width": 0x1}
            }
         }),
        # add on-each-point value, then change it (this was a bug)
        # parameter-8
        (None, None, (
            # "0", 0x0, # focus start value
            # "1", 0, # magnetic field start value
            # "2", 0, # tilt start value
            "3", "focus", # set focus series
            "4", "0x0", # start of focus series
            "5", "0x10", # step-width of focus series
            "6", "0xf0", # end of focus series
            "7", "tilt", # on-each-point
            "9", 0, # start of tilt
            "10", 1, # step width
            "11", 5, # end
            "7", "magnetic-field", # switch on-each-point
            "c" # continue
         ),
         {"focus": 0, "magnetic-field": 0, "tilt": 0},
         {"variable": "focus", "start": 0x0, "end": 0xf0, "step-width": 0x10, "on-each-point":
            {"variable": "magnetic-field", "start": 0.0, "end": 5.0, "step-width": 1.0}}),
        # # create magnetic field series from -5 to 5 with 1 stepwidth (invalid)
        # #   on each point focus series from -5 to 10 with stepwidth 1 (invalid)
        # (None, None, (
        #     "0", "magnetic-field", # magnetic field series
        #     "1", -5, # start (invalid)
        #     "2", 1, # step width
        #     "3", 5, # end
        #     "4", "focus", # on each point
        #         "6", -5, # start (invalid)
        #         "7", 1, # step width
        #         "8", 10, # end (invalid)
        #     "c" # continue
        #  ),
        #  {"focus": 0, "magnetic-field": 0, "tilt": 0},
        #  {"variable": "magnetic-field", "start": 0, "end": 5, "step-width": 1, "on-each-point":
        #     {"variable": "focus", "start": 0, "end": 5, "step-width": 1}
        #  }),
        # # create focus series from 1 to 3 with negative step width
        # (None, None, (
        #     "3", "magnetic-field", # vairable
        #     "4", 1, # start
        #     "5", -10, # step width
        #     "6", 3, # end
        #     "c" # continue
        #  ),
        #  {"focus": 0, "magnetic-field": 0, "tilt": 0},
        #  # step-width = max-min/10, min = 0, max = 5
        #  {"variable": "magnetic-field", "start": 1, "end": 3, "step-width": 0.5}),
    ])
    def test_show_create_measurement_loop(self, cliview, controller, start, series, user_inputs, expected_start, expected_series):
        """Test the _showCreateMeasurementLoop() function."""
        global writer

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = user_inputs
        if len(user_inputs) > 10:
            # a lot of redrawing of the view will raise an error because the 
            # maximum write count is reached even though there is no real
            # infinite loop
            writer.max_write_count = 1000

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = self.response_callback
        start, series = cliview._showCreateMeasurementLoop(controller, start, 
                                                           series)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        realprint(writer.io_log)

        assert expected_start == start
        assert expected_series == series
    
    @pytest.mark.usefixtures("cliview")
    def test_loader(self, cliview):
        """Test if the loader works."""
        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        cliview.progress_max = 100
        cliview.progress = 2
        cliview.showRunning()

        assert "2" in get_compare_text(writer.out_buffer)
        assert "100" in get_compare_text(writer.out_buffer)

        # auto update output
        cliview.progress = 55

        realprint(writer.out_buffer)

        # old text gets removed
        assert "2" not in get_compare_text(writer.out_buffer)
        # check new text
        assert "55" in get_compare_text(writer.out_buffer)
        assert "100" in get_compare_text(writer.out_buffer)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__
    
    @pytest.mark.usefixtures("cliview", "configuration")
    @pytest.mark.parametrize("user_inputs,expected_dict", [
        (("0", 100, # set key1 (options)
          "1", -9.81, # set key2 (options)
          "2", "String", # set key3 (already-set)
          "c" # continue
         ), 
         {"options": {"key1": 100, "key2": -9.81}, "already-set": {"key3": "String"}}
        )
    ])
    def test_show_settings(self, cliview, configuration, user_inputs, expected_dict):
        """Test if the settings work."""
        global writer

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = user_inputs

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer
        
        writer.input_response = self.response_callback
        values = cliview.showSettings(configuration)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        out = get_compare_text(writer.out_buffer)
        for group, key in configuration:
            assert group in out
            assert key in out

            try:
                assert configuration.getDescription(group, key) in out
            except KeyError:
                # there is no description
                pass
        
        assert values == expected_dict
        
    @pytest.mark.usefixtures("cliview", "configuration")
    @pytest.mark.parametrize("input_definition,value,expected", 
        default_valid_select_definition + [
            # default not required
            ({"datatype": int}, None, None),
            ({"datatype": float}, None, None),
            ({"datatype": bool}, None, None),
            ({"datatype": str}, None, None),
            # not required
            ({"datatype": int, "required": False}, None, None),
            ({"datatype": float, "required": False}, None, None),
            ({"datatype": bool, "required": False}, None, None),
            ({"datatype": str, "required": False}, None, None),
        ]
    )
    def test_parse_value(self, cliview, input_definition, value, expected):
        """Test if the _parseValue() function works."""

        assert cliview._parseValue(input_definition, value) == expected
        
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("input_definition,value", [
        # invalid types
        ({"datatype": int}, "str"),
        ({"datatype": float}, "nofloat"),
        ({"datatype": bool}, 4),
        # required is wrong
        ({"datatype": str, "required": True}, None),
        ({"datatype": str, "required": True}, None),
        # not in list
        ({"datatype": pylo.Datatype.options(["val1", "val2"])}, "val3"),
        # not in list casesensitive
        ({"datatype": pylo.Datatype.options(["val", "VAL"], exact_comparism=True)}, "vAl"),
        # not in boundaries
        ({"datatype": int, "min_value": 0, "max_value": 2}, 3),
        ({"datatype": int, "min_value": 0, "max_value": 2}, -1),
        ({"datatype": float, "min_value": -0.0001, "max_value": 0.0001}, 0.0002),
        ({"datatype": float, "min_value": -0.0001, "max_value": 0.0001}, -0.0002),
        ({"datatype": str, "min_value": "b", "max_value": "d"}, "a"),
        ({"datatype": str, "min_value": "b", "max_value": "d"}, "e")
    ])
    def test_parse_invalid_value(self, cliview, input_definition, value):
        """Test if the _parseValue() function works."""

        with pytest.raises(ValueError):
            cliview._parseValue(input_definition, value)
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("ask_definitions,text,user_inputs,expected", [
        (({"name": "Askval1", "datatype": str, "description": "Type in a str"},
          {"name": "Askval2", "datatype": int, "description": "Type in an int"},
          {"name": "Askval3", "datatype": float, "description": "Type in a float"}),
          "Input those values",
          ("0", "answerstr", # set Askval1
           "1", "10", # set Askval2
           "2", "-8328.8238", # set Askval3
           "c" # continue
          ), ("answerstr", 10, -8328.8238)),
    ])
    def test_ask_for(self, cliview, ask_definitions, text, user_inputs, expected):
        """Test if the _parseValue() function works."""
        global writer

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = user_inputs

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer
        
        writer.input_response = self.response_callback
        
        results = cliview.askFor(*ask_definitions, text=text)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        out = get_compare_text(writer.out_buffer)

        # check if text is printed
        assert text in out
        
        # check if names and descriptions are shown
        for definition in ask_definitions:
            assert definition["name"] in out
            assert definition["description"] in out

        # check results
        assert len(results) == len(expected)

        for i, r in enumerate(results):
            assert r == expected[i]
            assert type(r) == type(expected[i])
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("text,options,user_inputs,expected", [
        ("Example text", ("Yes", "No"), ("y", ), 0),
        ("Example text 2", ("Yes", "No"), ("Y", ), 0),
        ("Example text 3", ("Yes", "No"), ("N", ), 1),
        ("Example text 4", ("Yes", "No"), ("n", ), 1),
        ("Example text 5", ("Yes", "Yep", "no", "Nope"), (0, ), 0),
        ("Example text 6", ("Yes", "Yep", "no", "Nope"), (3, ), 3),
    ])
    def test_ask_for_decision(self, cliview, text, options, user_inputs, expected):
        """Test if asking for decision works."""
        global writer

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = user_inputs

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer
        
        writer.input_response = self.response_callback
        
        results = cliview.askForDecision(text, options)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        out = get_compare_text(writer.out_buffer)

        # check if text is printed
        assert text in out
        
        # check if names and descriptions are shown
        for option in options:
            assert option in out

        # check results
        assert results == expected
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("text,options,user_inputs,expected", [
        ("Example text", ("Yes", "No"), ("a", 0, "y"), 0),
        ("Example text 2", ("Yes", "No"), (1, 1, "m", "m", "M", "n"), 1),
        ("Example text 5", ("Yes", "Yep", "no", "Nope"), ("y", 1), 1),
        ("Example text 6", ("Yes", "Yep", "no", "Nope"), ("n", 2), 2),
    ])
    def test_ask_for_decision_invalid_inputs(self, cliview, text, options, user_inputs, expected):
        """Test if asking for decision works."""
        global writer

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = user_inputs

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer
        
        writer.input_response = self.response_callback
        
        results = cliview.askForDecision(text, options)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        out = get_compare_text(writer.out_buffer)

        # check if text is printed
        assert text in out

        # check that an error was printed
        assert "invalid" in out
        # check that the error was printed for each invalid input
        assert out.count("invalid") >= len(user_inputs) - 1
        # check that the response was asked for each input
        assert self.response_counter == len(user_inputs)
        
        # check if names and descriptions are shown
        for option in options:
            assert option in out

        # check results
        assert results == expected
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("ask_definitions,text,user_inputs,expected", [
        (({"name": "Askval1", "datatype": str, "description": "Type in a str"},
          {"name": "Askval2", "datatype": int, "description": "Type in an int"},
          {"name": "Askval3", "datatype": float, "description": "Type in a float"}),
          "Input those values",
          ("0", "answerstr", # set Askval1
           "1", "x", # empty Askval2, this should show an error
           "8", # set Askval2 after error
           "c", # continue, should show error because Askval3 is not set
           "2", "a", # abort setting Askval3
            "2", "1.01", # set Askval3
            "c" # continue
          ), ("answerstr", 8, 1.01)),
    ])
    def test_invalid_ask_for(self, cliview, ask_definitions, text, user_inputs, expected):
        """Test if the _parseValue() function works."""
        global writer

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = user_inputs

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer
        
        writer.input_response = self.response_callback
        
        results = cliview.askFor(*ask_definitions, text=text)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        out = get_compare_text(writer.out_buffer)

        # check if text is printed
        assert text in out

        # check if the continue was not performed
        assert "The values for" in out
        assert "are invalid" in out
        assert "(Details" in out

        # check if abort error is shown
        assert "is required" in out
        assert "You have to put in something" in out
        
        # check if names and descriptions are shown
        for definition in ask_definitions:
            assert definition["name"] in out
            assert definition["description"] in out

        # check results
        assert len(results) == len(expected)

        for i, r in enumerate(results):
            assert r == expected[i]
            assert type(r) == type(expected[i])
    
    @pytest.mark.usefixtures("cliview", "controller")
    @pytest.mark.parametrize("series,expected_series,add_defaults", [
        ({"variable": "focus"}, {"variable": "focus", "start": 0, "end": 0xfa, 
          "step-width": 0xfa / 10}, True),
        ({"variable": "focus", "on-each-point": {"variable": "magnetic-field"}}, 
         {"variable": "focus", "start": 0, "end": 0xfa, "step-width": 0xfa / 10,
          "on-each-point": {"variable": "magnetic-field", "start": 0, "end": 5, 
          "step-width": 0.5}}, True),
    ])
    def test_parse_series(self, cliview, controller, series, expected_series, add_defaults):
        """Test the parse series function."""

        series, errors = cliview.parseSeries(
            controller.microscope.supported_measurement_variables, series, 
            add_defaults
        )
        assert series == expected_series
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("tags,user_inputs,expected", [
        # modify elements
        ({"tag1": {"value": "Value 1", "save": True}, 
          "tag2": {"value": 2, "save": False},
          "tag3": {"value": False}}, 
          ("0", # edit tag1
           "Modified value", # change to value
           "3", # change save value of tag2
           "y",
           "4", # edit tag3
           "Modified value 2", # change to value
           "c", # confirm
          ), {"tag1": {"value": "Modified value", "save": True}, 
              "tag2": {"value": "2", "save": True},
              "tag3": {"value": "Modified value 2", "save": False}}),
        # delete elements
        ({"tag1": {"value": "Value 1", "save": False}, 
          "tag2": {"value": 2, "save": False},
          "tag3": {"value": False}}, 
          ("0", # edit tag1
           "!empty", # empty value
           "2", # edit tag3
           "!empty", # change to value
           "c", # confirm
          ), {"tag2": {"value": "2", "save": False}}),
        # # add elements
        ({"tag1": {"value": "Value 1", "save": False}}, 
          ("a", # add element
           "newtag2", # new tag name
           "2", # select new tag
           "new tag value 2", # change value
           "a", # add another element
           "newtag3", # new tag name
           "4", # seledct newtag3
           "new tag value 3", # change value
           "5", # select save value of newtag3
           "y", # set to true
           "0", # modify tag1
           "changed value", # change value of tag1
           "1", # change save value of tag1
           "y", # set to true
           "c", # confirm
          ), {"tag1": {"value": "changed value", "save": True},
              "newtag2": {"value": "new tag value 2", "save": False},
              "newtag3": {"value": "new tag value 3", "save": True}}),
    ])
    def test_show_custom_tags_loop(self, cliview, tags, user_inputs, expected):
        """Test if asking for decision works."""
        global writer

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = user_inputs

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer
        
        writer.input_response = self.response_callback
        
        results = cliview._showCustomTagsLoop(tags)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        # realprint(writer.io_log)

        # check results
        assert results == expected
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("tags,user_inputs,expected_config,expected_return", [
        # modify elements
        ({"tag1": "Value 1", "tag2": "Value 2", "tag3": "Value 3", 
          "tag4": "Value 4"}, 
          ("0", # edit tag1
           "Modified value", # change to value
           "2", # edit tag2
           "!empty", # remove tag 2
           "3", # edit tag3 save value
           "n", # set to false 
           "5", # edit tag4 save value
           "y", 
           "c", # confirm
          ), 
          {"tag1": "Modified value", "tag4": "Value 4"},
          {"tag1": "Modified value", "tag3": "Value 3", "tag4": "Value 4"}),
    ])
    def test_show_custom_tags(self, cliview, tags, user_inputs, expected_config, expected_return):
        """Test if asking for decision works."""
        global writer

        configuration = pylo.AbstractConfiguration()
        from pylo.config import CUSTOM_TAGS_GROUP_NAME

        for key, value in tags.items():
            configuration.setValue(CUSTOM_TAGS_GROUP_NAME, key, value)

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = user_inputs

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        writer.cls()
        sys.stdout = writer
        sys.stdin = writer
        
        writer.input_response = self.response_callback
        
        results = cliview.showCustomTags(configuration)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        realprint(writer.io_log)

        tags_config = {}
        for key in configuration.getKeys(CUSTOM_TAGS_GROUP_NAME):
            tags_config[key] = configuration.getValue(CUSTOM_TAGS_GROUP_NAME, key)

        # check results
        # assert len(results) == len(expected)
        assert tags_config == expected_config
        assert results == expected_return