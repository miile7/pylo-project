"""This file defines classes, mainly dummy classes replacing the real classes
for testing."""

import sys
import time

realstdout = sys.stdout

import pylo

def realprint(*values, sep=" ", end="\n"):
    print(sep.join(map(str, values)) + end, file=realstdout)


class DummyViewShowsError(AssertionError):
    pass

class DummyView(pylo.AbstractView):
    """A view that can be used for testing.

    Using askFor()
    --------------
    Use `ask_for_response` which contains the comparator at index 0 (one or 
    more strings that have to be in the name it is asked for) or a callable, 
    contains the repsonse or a callable at index 1
    >>> view.ask_for_response.append("match", "response")
    >>> view.ask_for_response.append(("all", "words", "required"), 
    ...                              lambda input_definition: "response")
    >>> view.ask_for_response.append(lambda input_definition: True,
    ...                              lambda input_definition: "response")
    """
    def __init__(self, *args, **kwargs):
        self.reset()
        super().__init__(*args, **kwargs)
    
    def clear(self):
        pass

    def reset(self):
        self.shown_create_measurement_times = []
        self.ask_for_response = []
        self.request_log = []
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
        self.request_log += inputs

        for i, inp in enumerate(self.inputs):
            if "name" in inp:
                for name_contains, response in self.ask_for_response:
                    is_correct_name = False

                    realprint(name_contains, response, inp["name"])

                    if (isinstance(name_contains, str) and 
                        name_contains in inp["name"]):
                        # name has to be equal
                        is_correct_name = True
                    elif isinstance(name_contains, (list, tuple)):
                        # all words have to be in the name
                        is_correct_name = True
                        for n in name_contains:
                            if not n in inp["name"]:
                                is_correct_name = False
                                break
                    elif callable(name_contains) and name_contains(inp):
                        # callback
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

        self.print("DummyView::showError() is called.")
        self.print("\t{}: {}".format(name, error))
        self.print("\tFix: {}".format(how_to_fix))
        
        # display errors, if they are inteded use pytest.raises()
        if isinstance(error, Exception):
            import traceback
            traceback.print_exc()

            raise DummyViewShowsError("{}".format(error)).with_traceback(error.__traceback__)
        else:
            raise DummyViewShowsError(error)

    def showHint(self, *args):
        self.print(*args)
    
    def print(self, *inputs, sep=" ", end="\n", inset=""):
        realprint(*inputs, sep=sep, end=end)
    
    def showSettings(self, configuration: "AbstractConfiguration", *args, **kwargs):
        return configuration.asDict()
    
    def _showCustomTags(self, tags):
        if not isinstance(tags, dict):
            return dict()
        else:
            return tags

class DummyConfiguration(pylo.AbstractConfiguration):
    def __init__(self):
        super().__init__()
    
    def loadConfiguration(self):
        pass
    
    def saveConfiguration(self):
        pass