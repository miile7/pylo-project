"""This file defines classes, mainly dummy classes replacing the real classes
for testing."""

import sys
import math
import time
import typing

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

def get_equality(v1: typing.Any, v2: typing.Any, 
                 rel_tol: typing.Optional[typing.Union[int, float]]=0, 
                 abs_tol: typing.Optional[typing.Union[int, float]]=1e-6, 
                 default_return: typing.Optional[typing.Any]=True):
    """Test whether the two values `v1` and `v2` are equal.

    This returns True if both values are equal, False otherwise. If `v1` and 
    `v2` both are mappings or both are sequences, they are converted to dicts
    or lists and their elements will be compared by keys. If one key is missing
    or if the values are not equal, False is returned. Nested maps and 
    sequences are supported.

    The `rel_tol` and the `abs_tol` can be used to define tolerances. The
    `default_return` is returned if the values neither are numbers nor 
    sequences nor dicts.

    If the `v1` and `v2` types are incompatible False is returned.

    Parameters
    ----------
    v1, v2 : any
        The values to compare
    rel_tol, abs_tol : int or float, optional
        The relative and absolute tolerances, defaults are 0 and 1e-6
    default_return : any, optional
        The value to return if `v1` and `v2` or their elements are not numbers
    
    Returns
    -------
    boolean or type of `default_return`
        Whether the `v1` and `v2` are approximately equal or not
    """

    if (isinstance(v1, (int, float, complex)) and 
        isinstance(v2, (int, float, complex))):
        return math.isclose(v1, v2, rel_tol=rel_tol, abs_tol=abs_tol)
    elif isinstance(v1, str) and isinstance(v2, str):
        return default_return
    elif isinstance(v1, str) or isinstance(v2, str):
        return False
    else:
        try:
            v1 = dict(v1)
            v2 = dict(v2)

            for k in set(v1.keys()) | set(v2.keys()):
                if k not in v1 or k not in v2:
                    return False
                elif not get_equality(v1[k], v2[k], rel_tol, abs_tol, default_return):
                    return False
            
            return True
        except ValueError:
            pass
            
        try:
            v1 = list(v1)
            v2 = list(v2)
            
            if len(v1) != len(v2):
                return False
            else:
                for e1, e2 in zip(v1, v2):
                    if not get_equality(e1, e2, rel_tol, abs_tol, default_return):
                        return False
            
            return True
        except ValueError:
            pass
        
        return default_return