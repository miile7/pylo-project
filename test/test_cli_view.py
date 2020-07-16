import os
import sys

if __name__ == "__main__":
    # For direct call only
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class DummyOut:
    def __init__(self):
        self.out_buffer = ""
        self.input_response = ""
        self.cls()

    def write(self, text):
        self.write_counter += 1
        if self.write_counter > 250:
            realprint(self.out_buffer)
            raise RecursionError("Too many calls of write().")
        self.out_buffer += text
    
    def flush(self):
        pass
    
    def read(self):
        self.read_counter += 1
        if self.read_counter > 250:
            realprint(self.out_buffer)
            raise RecursionError("Too many calls of read().")
        
        if callable(self.input_response):
            return self.input_response()
        else:
            return self.input_response
    
    def readline(self):
        return str(self.read()) + "\n"
    
    def cls(self):
        self.read_counter = 0
        self.write_counter = 0
        self.out_buffer = ""

writer = DummyOut()

import re
import string
import pytest
import random

import pylo

real_std_out = sys.stdout
def realprint(*values, sep=" ", end="\n"):
    global real_std_out
    print(sep.join(map(str, values)) + end, file=real_std_out)

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

default_valid_select_definition = [
    # string
    ({"label": "Label a", "id": "testid", "datatype": str, "value": "", 
        "required": True}, "testinput", "testinput"),
    # int
    ({"label": "Label b", "id": "testid", "datatype": int, "value": 5, 
        "required": True, "min_value": 2, "max_value": 10}, "10", 10),
    ({"label": "Label c", "id": "testid", "datatype": int, "value": 5, 
        "required": True, "min_value": 2, "max_value": 10}, "2", 2),
    # float
    ({"label": "Label d", "id": "testid", "datatype": float, "value": 0, 
        "required": True, "min_value": -1.25, "max_value": 1.25}, "-1.25", -1.25),
    ({"label": "Label e", "id": "testid", "datatype": float, "value": 0, 
        "required": True, "min_value": -1.25, "max_value": 1.25}, "1.25", 1.25),
    # min *or* max, not both
    ({"label": "Label f", "id": "testid", "datatype": int, "value": 2, 
        "required": True, "min_value": -10}, "-10", -10),
    ({"label": "Label g", "id": "testid", "datatype": float, "value": -22, 
        "required": True, "max_value": -10}, "-10", -10.0),
    # all boolean possibilites
    ({"label": "Label h", "id": "testid", "datatype": bool, "value": True, 
        "required": True}, "tRuE", True),
    ({"label": "Label i", "id": "testid", "datatype": bool, "value": False, 
        "required": True}, "t", True),
    ({"label": "Label j", "id": "testid", "datatype": bool, "value": False, 
        "required": True}, "yes", True),
    ({"label": "Label k", "id": "testid", "datatype": bool, "value": False, 
        "required": True}, "y", True),
    ({"label": "Label l", "id": "testid", "datatype": bool, "value": False, 
        "required": True}, "on", True),
    ({"label": "Label m", "id": "testid", "datatype": bool, "value": True, 
        "required": True}, "fAlSe", False),
    ({"label": "Label n", "id": "testid", "datatype": bool, "value": True, 
        "required": True}, "f", False),
    ({"label": "Label o", "id": "testid", "datatype": bool, "value": True, 
        "required": True}, "no", False),
    ({"label": "Label p", "id": "testid", "datatype": bool, "value": True, 
        "required": True}, "n", False),
    ({"label": "Label q", "id": "testid", "datatype": bool, "value": True, 
        "required": True}, "off", False),
    # possibility list
    ({"label": "Label r", "id": "testid", "datatype": ["d", "b"], "value": "d", 
        "required": True}, "b", "b"),
    ({"label": "Label s", "id": "testid", "datatype": ["d", "b"], "value": "d", 
        "required": True}, "B", "b"),
    # abort command and empty commands are possibilities
    ({"label": "Label t", "id": "testid", "datatype": ["a", "x"], "value": "a", 
        "required": True}, "a", "a"),
    ({"label": "Label u", "id": "testid", "datatype": ["a", "x"], "value": "a", 
        "required": True}, "x", "x")
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
        ({"label": "Label v", "id": "testid", "datatype": str, "value": "", 
            "required": False}, "!empty", None),
        ({"label": "Label w", "id": "testid", "datatype": int, "value": 5, 
            "required": False}, "x", None),
        # not required by default
        ({"label": "Label x", "id": "testid", "datatype": float, "value": 5.5}, 
            "x", None),
        ({"label": "Label y", "id": "testid", "datatype": bool, "value": False}, 
            "x", None),
        ({"label": "Label z", "id": "testid", "datatype": ["d", "b"], "value": "d"}, 
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
            if isinstance(input_definition["datatype"], list):
                assert inp in input_definition["datatype"]
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
        ({"label": "Testinput", "id": "testid", "datatype": ["d", "b"], "value": "d", 
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
        if isinstance(input_definition["datatype"], list):
            assert inp in input_definition["datatype"]
        else:
            assert type(inp) == input_definition["datatype"]
        
        assert type(inp) == type(expected)
        assert inp == expected
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("input_definition,user_input", [
        ({"label": "Testinput", "id": "testid", "datatype": str, "value": "a", 
          "required": True}, "!abort"),
        ({"label": "Testinput", "id": "testid", "datatype": int, "value": 5, 
          "min_value": 2, "max_value": 10}, "a"),
        ({"label": "Testinput", "id": "testid", "datatype": bool, "value": False}, 
          "a"),
        ({"label": "Testinput", "id": "testid", "datatype": ["x", "a"], 
          "value": "x"}, "!abort"),
        ({"label": "Testinput", "id": "testid", "datatype": ["x", "a", "!abort"], 
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
        ({"label": "Testinput", "id": "testid", "datatype": int, "value": 5, 
          "required": True, "min_value": 2, "max_value": 10}, "x", "10", 10),
        ({"label": "Testinput", "id": "testid", "datatype": float, "value": 5, 
          "required": True, "min_value": -38939.232, "max_value": 1}, "x", 
          "-323.25", -323.25),
        ({"label": "Testinput", "id": "testid", "datatype": ["a", "b"], "value": "a", 
          "required": True}, "x", "b", "b"),
        ({"label": "Testinput", "id": "testid", "datatype": ["x", "c"], "value": "x", 
          "required": True}, "!empty", "c", "c"),
        ({"label": "Testinput", "id": "testid", "datatype": ["x", "c", "!empty"], 
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
        if isinstance(input_definition["datatype"], list):
            assert inp in input_definition["datatype"]
        else:
            assert type(inp) == input_definition["datatype"]
        
        assert type(inp) == type(expected)
        assert inp == expected
    
    @pytest.mark.usefixtures("cliview")
    @pytest.mark.parametrize("select_definition", [default_valid_select_definition])
    def test_print_select_output(self, cliview, select_definition):
        """Test the print select output."""
        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        global writer

        expected_value = [d[2] for d in select_definition]
        user_inputs = [d[1] for d in select_definition]
        select_definition = [d[0] for d in select_definition]

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
        (default_valid_select_definition, ("c", ), True),
        # quit
        (default_valid_select_definition, ("q", ), False),
        # set any value
        (default_valid_select_definition, ("0", "random text"), None),
        # set any value, then abort
        (default_valid_select_definition, ("0", "c"), None),
    ])
    def test_print_select_command_returns(self, cliview, select_definition, commands, expected):
        """Test the print select output."""
        # doesn't work to keep it in the fixture, has to be explicit every 
        # time :(
        global writer

        expected_value = [d[2] for d in select_definition]
        user_inputs = [d[1] for d in select_definition]
        select_definition = [d[0] for d in select_definition]

        self.response_counter = 0
        self.out_buffers = []
        self.response_answers = commands

        writer.cls()
        sys.stdout = writer
        sys.stdin = writer

        writer.input_response = self.response_callback
        values, command_return = cliview._printSelect(*select_definition)

        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__

        assert command_return == expected