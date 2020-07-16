import os
import sys

if __name__ == "__main__":
    # For direct call only
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class DummyOut:
    def __init__(self):
        self.out_buffer = ""
        self.input_response = ""

    def write(self, text):
        self.out_buffer += text
    
    def flush(self):
        pass
    
    def read(self):
        if callable(self.input_response):
            return self.input_response()
        else:
            return self.input_response
    
    def readline(self):
        return str(self.read()) + "\n"
    
    def cls(self):
        self.out_buffer = ""

writer = DummyOut()

import re
import pytest
import random

import pylo

def realprint(*values, sep=" ", end="\n"):
    print(sep.join(map(str, values)) + end, file=sys.__stdout__)

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
    sys.stdout = writer
    sys.stdin = writer

    yield pylo.CLIView()

    sys.stdout = sys.__stdout__
    sys.stdin = sys.__stdin__

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
    @pytest.mark.parametrize("input_definition,user_input,expected", [
        # string
        ({"label": "Testinput", "id": "testid", "datatype": str, "value": "", 
          "required": True}, "testinput", "testinput"),
        # int
        ({"label": "Testinput", "id": "testid", "datatype": int, "value": 5, 
          "required": True, "min_value": 2, "max_value": 10}, "10", 10),
        ({"label": "Testinput", "id": "testid", "datatype": int, "value": 5, 
          "required": True, "min_value": 2, "max_value": 10}, "2", 2),
        # float
        ({"label": "Testinput", "id": "testid", "datatype": float, "value": 0, 
          "required": True, "min_value": -1.25, "max_value": 1.25}, "-1.25", -1.25),
        ({"label": "Testinput", "id": "testid", "datatype": float, "value": 0, 
          "required": True, "min_value": -1.25, "max_value": 1.25}, "1.25", 1.25),
        # min *or* max, not both
        ({"label": "Testinput", "id": "testid", "datatype": int, "value": 2, 
          "required": True, "min_value": -10}, "-10", -10),
        ({"label": "Testinput", "id": "testid", "datatype": float, "value": -22, 
          "required": True, "max_value": -10}, "-10", -10.0),
        # all boolean possibilites
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": True, 
          "required": True}, "tRuE", True),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": False, 
          "required": True}, "t", True),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": False, 
          "required": True}, "yes", True),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": False, 
          "required": True}, "y", True),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": False, 
          "required": True}, "on", True),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": True, 
          "required": True}, "fAlSe", False),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": True, 
          "required": True}, "f", False),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": True, 
          "required": True}, "no", False),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": True, 
          "required": True}, "n", False),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": True, 
          "required": True}, "off", False),
        # possibility list
        ({"label": "Testinput", "id": "testid", "datatype": ["a", "b"], "value": "a", 
          "required": True}, "b", "b"),
        ({"label": "Testinput", "id": "testid", "datatype": ["a", "b"], "value": "a", 
          "required": True}, "B", "b"),
        # cancel command and empty commands are possibilities
        ({"label": "Testinput", "id": "testid", "datatype": ["c", "x"], "value": "a", 
          "required": True}, "c", "c"),
        ({"label": "Testinput", "id": "testid", "datatype": ["c", "x"], "value": "a", 
          "required": True}, "x", "x"),
    ])
    def test_input_value_loop_valid_values(self, cliview, input_definition, user_input, expected):
        """Test if the _inputValueLoop() function with valid user inputs."""
        global writer

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
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
        
        # check returned value
        if isinstance(input_definition["datatype"], list):
            assert inp in input_definition["datatype"]
        else:
            assert type(inp) == input_definition["datatype"]
        
        assert type(inp) == type(expected)
        assert inp == expected
    
    def response_callback(self):
        """The callback for the user input response."""
        self.response_counter += 1
        return self.response_answers[(self.response_counter - 1) % len(self.response_answers)]
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("input_definition,user_input1,user_input2,expected", [
        # wrong types
        ({"label": "Testinput", "id": "testid", "datatype": int, "value": 5, 
          "required": True, "min_value": 2, "max_value": 10}, "invalid", "10", 10),
        ({"label": "Testinput", "id": "testid", "datatype": float, "value": 5, 
          "required": True, "min_value": -38939.232, "max_value": 1}, "invalid", "-323.25", -323.25),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": True, 
          "required": True}, "ney", "no", False),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": False, 
          "required": True}, "yep", "yes", True),
        # not in boundaries
        ({"label": "Testinput", "id": "testid", "datatype": int, "value": 5, 
          "required": True, "min_value": 2, "max_value": 10}, "1", "2", 2),
        ({"label": "Testinput", "id": "testid", "datatype": int, "value": 4, 
          "required": True, "min_value": 2, "max_value": 10}, "22", "5", 5),
        ({"label": "Testinput", "id": "testid", "datatype": float, "value": 0, 
          "required": True, "min_value": -1.25, "max_value": 1.25}, "-1.26", "-1.25", -1.25),
        ({"label": "Testinput", "id": "testid", "datatype": float, "value": 0, 
          "required": True, "min_value": -1.25, "max_value": 1.25}, "1.26", "1.125", 1.125),
        ({"label": "Testinput", "id": "testid", "datatype": int, "value": 2, 
          "required": True, "min_value": -10}, "-33", "99999", 99999),
        ({"label": "Testinput", "id": "testid", "datatype": float, "value": -22, 
          "required": True, "max_value": -10}, "-6.4334", "-10", -10.0),
        # not in possibilities
        ({"label": "Testinput", "id": "testid", "datatype": ["a", "b"], "value": "a", 
          "required": True}, "d", "b", "b"),
    ])
    def test_input_value_loop_invalid_values(self, cliview, input_definition, user_input1, user_input2, expected):
        """Test if the _inputValueLoop() function with invalid user inputs."""
        global writer

        num_wrong_answers = random.randint(1, 4)
        self.response_counter = 0
        self.response_answers = [user_input1] * num_wrong_answers + [user_input2]

        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = self.response_callback
        inp = cliview._inputValueLoop(input_definition)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__
        
        # check if asked the correct amount of times
        assert self.response_counter == num_wrong_answers + 1

        # check returned value
        if isinstance(input_definition["datatype"], list):
            assert inp in input_definition["datatype"]
        else:
            assert type(inp) == input_definition["datatype"]
        
        assert type(inp) == type(expected)
        assert inp == expected