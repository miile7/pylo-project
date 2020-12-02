import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import math
import copy
import time
import random
import pytest

import pylo

class DummyMicroscope1(pylo.MicroscopeInterface):
    def __init__(self, controller):
        super().__init__(controller)
        self.clear()

    def clear(self):
        self.init_time = time.time()
        self.performed_steps = []

        self.registerMeasurementVariable(
            pylo.MeasurementVariable("a", "A", 1, 3),
            lambda: self.getVar("a"), lambda x: self.setVar("a", x)
        )
        self.registerMeasurementVariable(
            pylo.MeasurementVariable("b", "B", 4, 7),
            lambda: self.getVar("b"), lambda x: self.setVar("b", x)
        )
        self.registerMeasurementVariable(
            pylo.MeasurementVariable("c", "C", 0, 10),
            lambda: self.getVar("c"), lambda x: self.setVar("c", x)
        )
        self.registerMeasurementVariable(
            pylo.MeasurementVariable("d", "D", -5, 5),
            lambda: self.getVar("d"), lambda x: self.setVar("d", x)
        )
    
    def setInLorentzMode(self, lorentz_mode):
        pass
    
    def getInLorentzMode(self):
        return True
    
    def setVar(self, id_, value):
        self.performed_steps.append((id_, value, time.time()))
    
    def getVar(self, id_):
        for k, v, t in reversed(self.performed_steps):
            if id_ == k:
                return v
            
        return None
    
    def resetToSafeState(self):
        pass

class DummyMicroscope2(pylo.MicroscopeInterface):
    def __init__(self, controller):
        super().__init__(controller)
        self.clear()

    def clear(self):
        self.init_time = time.time()
        self.performed_steps = []

        self.supported_measurement_variables = [
            pylo.MeasurementVariable("focus", "Focus", 0, 10, "mA"),
            pylo.MeasurementVariable("lense-current", "OM Current", 0, 3, 
                                     format=pylo.Datatype.hex_int,
                                     calibration=2, calibrated_unit="T",
                                     calibrated_name="Magnetic Field"),
            pylo.MeasurementVariable("x-tilt", "Tilt (x direction)", -35, 35, "deg")
        ]
    
    def setInLorentzMode(self, lorentz_mode):
        pass
    
    def getInLorentzMode(self):
        return True
    
    def setVar(self, id_, value):
        self.performed_steps.append((id_, value, time.time()))
    
    def getVar(self, id_):
        for k, v, t in reversed(self.performed_steps):
            if id_ == k:
                return v
            
        return None
    
    def resetToSafeState(self):
        pass

values = {
    "a": range(1, 4, 1), # [1, 2, 3]
    "b": range(4, 8, 1), # [4, 5, 6, 7]
    "c": range(2, 10, 2), # [2, 4, 6, 8] (make sure to stop at 10, otherwise 
                          #               the test series is initialized wrong)
    "d": range(-5, 10, 5) # [-5, 0, 5] (make sure to stop at 10, otherwise 
                          #             the test series is initialized wrong)
}

@pytest.fixture()
def controller():
    controller = pylo.Controller(pylo.AbstractView(), pylo.AbstractConfiguration())
    controller.microscope = DummyMicroscope2(controller)
    return controller

@pytest.fixture()
@pytest.mark.usefixtures("controller")
def measurement_steps(controller):
    controller = pylo.Controller(pylo.AbstractView(), pylo.AbstractConfiguration())
    controller.microscope = DummyMicroscope1(controller)
    start = {"a": values["a"].start, "b": values["b"].start,
             "c": values["c"].start, "d": values["d"].start}
    series = {
        "variable": "a", 
        "start": values["a"].start, 
        "step-width": values["a"].step, 
        "end": values["a"].stop - values["a"].step, 
        "on-each-point": {
            "variable": "b", 
            "start": values["b"].start, 
            "step-width": values["b"].step, 
            "end": values["b"].stop - values["b"].step, 
            "on-each-point": {
                "variable": "c", 
                "start": values["c"].start, 
                "step-width": values["c"].step, 
                "end": values["c"].stop - values["c"].step, 
                "on-each-point": {
                    "variable": "d", 
                    "variable": "d", 
                    "start": values["d"].start, 
                    "step-width": values["d"].step, 
                    "end": values["d"].stop - values["d"].step,
                }
            }
        }
    }
    return pylo.MeasurementSteps(controller, start, series)

class TestMeasurementSteps:
    @pytest.mark.usefixtures("measurement_steps")
    def test_count(self, measurement_steps):
        """Test the length of the measurement steps"""
        assert len(measurement_steps) == (len(values["a"]) * 
                                          len(values["b"]) * 
                                          len(values["c"]) *
                                          len(values["d"]))
                                        
    @pytest.mark.usefixtures("measurement_steps")
    def test_nest_lengths(self, measurement_steps):
        """Test the length of each nest series"""
        assert list(measurement_steps._getNestLengths()) == [len(values["a"]),
                                                             len(values["b"]), 
                                                             len(values["c"]),
                                                             len(values["d"])]
                                        
    @pytest.mark.usefixtures("measurement_steps")
    def test_nest_series(self, measurement_steps):
        """Test the nest series"""
        series = measurement_steps.series
        nests = list(measurement_steps._getNestSeries())
        for i, s in enumerate(nests):
            assert s == series

            if i + 1 < len(nests):
                assert "on-each-point" in s
                assert isinstance(s["on-each-point"], dict)
                series = s["on-each-point"]
                                        
    @pytest.mark.usefixtures("measurement_steps")
    def test_getitem(self, measurement_steps):
        """Test the nest series"""
        
        index = 0
        for a in values["a"]:
            for b in values["b"]:
                for c in values["c"]:
                    for d in values["d"]:
                        step = measurement_steps.__getitem__(index)

                        assert isinstance(step, dict)
                        assert step["a"] == a
                        assert step["b"] == b
                        assert step["c"] == c
                        assert step["d"] == d

                        index += 1
                                        
    @pytest.mark.usefixtures("measurement_steps")
    def test_next(self, measurement_steps):
        """Test the iteration over the measurement_steps"""

        steps = []
        i = 0
        measurement_steps.__iter__()
        while True:
            try:
                steps.append(measurement_steps.__next__())
            except StopIteration:
                break

        index = 0
        for a in values["a"]:
            for b in values["b"]:
                for c in values["c"]:
                    for d in values["d"]:
                        step = steps[index]

                        assert isinstance(step, dict)
                        assert step["a"] == a
                        assert step["b"] == b
                        assert step["c"] == c
                        assert step["d"] == d

                        index += 1
                                        
    @pytest.mark.usefixtures("measurement_steps")
    def test_iteration(self, measurement_steps):
        """Test the iteration over the measurement_steps"""

        steps = []
        for step in measurement_steps:
            steps.append(step)

        index = 0
        for a in values["a"]:
            for b in values["b"]:
                for c in values["c"]:
                    for d in values["d"]:
                        step = steps[index]

                        assert isinstance(step, dict)
                        assert step["a"] == a
                        assert step["b"] == b
                        assert step["c"] == c
                        assert step["d"] == d

                        index += 1
                                        
    @pytest.mark.usefixtures("measurement_steps")
    def test_crosscheck_next_getitem_iterator(self, measurement_steps):
        """Test the whether the iteration returns the same as the getitem 
        method"""

        iter_steps = []
        for step in measurement_steps:
            iter_steps.append(step)
        
        measurement_steps.__iter__()
        i = 0
        while True:
            try:
                next_step = measurement_steps.__next__()
            except StopIteration:
                # make sure that when the iteration ends, the __getitem__
                # also ends
                with pytest.raises(IndexError):
                    measurement_steps.__getitem__(i)
                assert len(iter_steps) == i
                break
            
            getitem_step = measurement_steps.__getitem__(i)
            iter_step = iter_steps[i]

            assert getitem_step == iter_step
            assert iter_step == next_step
            assert next_step == getitem_step

            i += 1
    
    @pytest.mark.usefixtures("controller")
    def test_parse_series(self, controller):
        """Test if the Measurement::_parseSeries() is correct for a single 
        series."""
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1}

        steps = pylo.MeasurementSteps(controller, start, series)

        assert len(steps) == 11

        for i, step in enumerate(steps):
            # make sure that the MeasurementSteps.__next__() function returns 
            # the same as the MeasurementSteps.__getitem__()
            assert steps[i] == step

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
    
    @pytest.mark.usefixtures("controller")
    def test_parse_single_nested_series(self, controller):
        """Test if the Measurement::_parseSeries() is correct for a series 
        that contains another series."""
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1, 
                  "on-each-point": {"variable": "lense-current", "start": 0, 
                                   "end": 3, "step-width": 0.1}}

        steps = pylo.MeasurementSteps(controller, start, series)

        assert len(steps) == 11 * 31

        for i, step in enumerate(steps):
            getitem_step = steps[i]
            print(i, step, getitem_step)

            # make sure that the MeasurementSteps.__next__() function returns 
            # the same as the MeasurementSteps.__getitem__()
            for key in set(list(getitem_step.keys()) + list(step.keys())):
                assert key in getitem_step
                assert key in step
                assert math.isclose(getitem_step[key], step[key])

            print("")

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
    
    @pytest.mark.usefixtures("controller")
    def test_parse_double_nested_series(self, controller):
        """Test if the Measurement::_parseSeries() is correct for a series 
        that contains another series and that contains another series."""

        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1, 
                  "on-each-point": {"variable": "lense-current", "start": 0, 
                                   "end": 3, "step-width": 0.1, 
                                   "on-each-point": {"variable": "x-tilt", 
                                                     "start": -20, 
                                                     "end": 20, 
                                                     "step-width": 5}}}

        steps = pylo.MeasurementSteps(controller, start, series)

        assert len(steps) == 11 * 31 * 9

        for i, step in enumerate(steps):
            getitem_step = steps[i]
            print(i, step, getitem_step)

            # make sure that the MeasurementSteps.__next__() function returns 
            # the same as the MeasurementSteps.__getitem__()
            for key in set(list(getitem_step.keys()) + list(step.keys())):
                assert key in getitem_step
                assert key in step
                assert math.isclose(getitem_step[key], step[key])

            print("")
            continue

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
    
    @pytest.mark.usefixtures("controller")
    def test_parse_change_start_parameters(self, controller):
        """Test if the MeasurementSteps() changes the start parameters to the 
        series start parameters if they are different."""

        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 1, "end": 10, "step-width": 1, 
                  "on-each-point": {"variable": "lense-current", "start": 1, 
                                   "end": 3, "step-width": 0.1, 
                                   "on-each-point": {"variable": "x-tilt", 
                                                     "start": 10, 
                                                     "end": 20, 
                                                     "step-width": 5}}}

        steps = pylo.MeasurementSteps(controller, start, series)

        assert steps.start["focus"] == 1
        assert steps.start["lense-current"] == 1
        assert steps.start["x-tilt"] == 10
    
    @pytest.mark.usefixtures("controller")
    def test_parse_series_wrong_variable_raises_exception(self, controller):
        """Test if an invalid variable id raises an exception."""
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "non-existing", "start": 0, "end": 10, "step-width": 1}

        with pytest.raises(ValueError):
            pylo.MeasurementSteps(controller, start, series)
    
    @pytest.mark.usefixtures("controller")
    def test_parse_series_missing_key_raises_exception(self, controller):
        """Test if missing keys raise an exception."""
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1}

        for key in series:
            invalid_series = copy.deepcopy(series)
            del invalid_series[key]

            with pytest.raises(KeyError):
                pylo.MeasurementSteps(controller, start, invalid_series)
    
    @pytest.mark.usefixtures("controller")
    def test_parse_series_missing_key_in_subseries_raises_exception(self, controller):
        """Test if missing keys raise an exception."""
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": 1,
                  "on-each-point": {"variable": "x-tilt", "start": -5, "end": 5,
                                   "step-width": 5}}

        for key in series["on-each-point"]:
            invalid_series = copy.deepcopy(series)
            del invalid_series["on-each-point"][key]

            with pytest.raises(KeyError):
                pylo.MeasurementSteps(controller, start, invalid_series)

    @pytest.mark.parametrize("step_width", (-1, 0))
    @pytest.mark.usefixtures("controller")
    def test_parse_series_step_width_smaller_than_zero(self, step_width, controller):
        """Test if a step with smaller or equal to zero raises an exception."""
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "focus", "start": 0, "end": 10, "step-width": step_width}

        with pytest.raises(ValueError):
            pylo.MeasurementSteps(controller, start, series)

    @pytest.mark.usefixtures("controller")
    def test_parse_series_wrong_boundaries_raises_exception(self, controller):
        """Test if an exception is raised when the value is out of the 
        boundaries."""
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        
        for var in controller.microscope.supported_measurement_variables:
            wrong_start_series = {"variable": var.unique_id, 
                                  "start": var.min_value - random.randint(1, 100),
                                  "end": var.max_value,
                                  "step-width": 1}
            with pytest.raises(ValueError):
                pylo.MeasurementSteps(controller, start, wrong_start_series)

            wrong_end_series = {"variable": var.unique_id, 
                                "start": var.min_value,
                                "end": var.max_value + random.randint(1, 100),
                                "step-width": 1}
            with pytest.raises(ValueError):
                pylo.MeasurementSteps(controller, start, wrong_end_series)

    @pytest.mark.usefixtures("controller")
    def test_parse_series_uneven_step_width_stays_in_boundaries(self, controller):
        """Test if the all the steps are in the boundaries if the step width 
        does not fit even times in the range between start and end
        (e.g. start=1, end=2, step-width = 0.6)."""
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        
        for var in controller.microscope.supported_measurement_variables:
            series = {"variable": var.unique_id, "start": var.min_value,
                      "end": var.max_value, 
                      "step-width": (var.max_value - var.min_value) * 2 / 3}
            
            steps = pylo.MeasurementSteps(controller, start, series)

            for s in steps:
                assert var.min_value <= s[var.unique_id]
                assert s[var.unique_id] <= var.max_value

    @pytest.mark.usefixtures("controller")
    def test_parse_series_too_big_step_width_stays_in_boundaries(self, controller):
        """Test if the all the steps are in the boundaries if the step width 
        is bigger than the range between start and end
        (e.g. start=1, end=2, step-width = 4)."""
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        
        for var in controller.microscope.supported_measurement_variables:
            series = {"variable": var.unique_id, "start": var.min_value,
                      "end": var.max_value, 
                      "step-width": (var.max_value - var.min_value) * 4}
            
            steps = pylo.MeasurementSteps(controller, start, series)

            for i, s in enumerate(steps):
                # make sure that the MeasurementSteps.__next__() function returns 
                # the same as the MeasurementSteps.__getitem__()
                assert steps[i] == s

                assert var.min_value <= s[var.unique_id]
                assert s[var.unique_id] <= var.max_value
    
    @pytest.mark.usefixtures("controller")
    def test_parse_series_missing_key_in_start_conditions_raises_exception(self, controller):
        """Test if a value out of the boundaries in the start conditions raises
        an exception."""
        start = {"focus": 0, "lense-current": 0, "x-tilt": 0}
        series = {"variable": "lense-current", "start": 0, "end": 3, "step-width": 1}

        for key in start:
            invalid_start = copy.deepcopy(start)
            del invalid_start[key]
            
            if key != series["variable"]:
                with pytest.raises(KeyError):
                    pylo.MeasurementSteps(controller, start, invalid_start)
    
    @pytest.mark.usefixtures("controller")
    def test_parse_series_wrong_value_in_start_conditions_raises_exception(self, controller):
        """Test if a missing measuremnet variable in the start conditions 
        raises an exception."""
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
                pylo.MeasurementSteps(controller, start_too_small, series)
            
            start_too_big = start.copy()
            start_too_big[var.unique_id] = var.max_value + random.randint(1, 100)

            # if the series variable is given, it defines the start conditions
            if var.unique_id == series["variable"]:
                series["start"] = start_too_big[var.unique_id]

            with pytest.raises(ValueError):
                pylo.MeasurementSteps(controller, start_too_big, series)