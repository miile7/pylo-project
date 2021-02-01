import random
import pytest
import datetime

import pylo
from pylo import pylolib

class TestPylolib:
    @pytest.mark.parametrize("text,groups", [
        ("A", [("_", "A")]),
        ("A{?B}C", [("_", "A"), ("?", "B"), ("_", "C")]),
        ("A{{?B}C", [("_", "A{{?B}C")]),
        ("{?B}C", [("?", "B"), ("_", "C")]),
        ("A{?B}", [("_", "A"), ("?", "B")]),
        ("A{!B{C}}D", [("_", "A"), ("!", "B{C}}D")]),
        ("A{!B{C} }D", [("_", "A"), ("!", "B{C} "), ("_", "D")]),
        ("A{_B{C}}}D", [("_", "A"), ("_", "B{C}}}D")]),
        ("A{??B{C} }D", [("_", "A"), ("?", "?B{C} "), ("_", "D")]),
        ("A{!{_B}{C}D}E", [("_", "A"), ("!", "{_B}{C}D"), ("_", "E")]),
    ])
    def test_split_expand_vars_groups(self, text, groups):
        assert pylolib._split_expand_vars_groups(text) == groups
    
    def formatVar(self, var, val):
        if var.has_calibration:
            val = var.ensureCalibratedValue(val)
        
        if var.has_calibration and isinstance(var.calibrated_format, pylo.Datatype):
            val = pylolib.format_value(var.calibrated_format, val)
        elif isinstance(var.format, pylo.Datatype):
            val = pylolib.format_value(var.format, val)
        
        return val
    
    def test_expand_vars(self):
        controller = pylo.Controller(pylo.AbstractView(), 
                                     pylo.AbstractConfiguration())
        controller.microscope = pylo.loader.getDevice("Dummy Microscope", 
                                                      controller)
        controller.camera = pylo.loader.getDevice("Dummy Camera", controller)
        
        text = []
        check = []
        series = {}
        start = {}
        s = series
        for i, var in enumerate(controller.microscope.supported_measurement_variables):
            s["variable"] = var.unique_id
            s["start"] = pylolib.parse_value(var.format, 
                random.uniform(var.min_value, var.max_value / 2))
            s["end"] = pylolib.parse_value(var.format, 
                random.uniform(var.max_value / 2, var.max_value))
            s["step-width"] = pylolib.parse_value(var.format, 
                (s["end"] - s["start"]) / 5)
            
            start[var.unique_id] = s["start"]
            
            if var.has_calibration and isinstance(var.calibrated_name, str):
                name = var.calibrated_name
            else:
                name = var.name
            
            if var.has_calibration and isinstance(var.calibrated_unit, str):
                unit = var.calibrated_unit
            else:
                unit = var.unit
            
            text.append("id: {{varname[{}]}}".format(var.unique_id))
            check.append(("id", name))
            text.append("unit: {{varunit[{}]}}".format(var.unique_id))
            check.append(("unit", unit))

            text.append("step: {{step[{}]}}".format(var.unique_id))
            check.append(("step", ("step", var.unique_id)))
            text.append("hstep: {{humanstep[{}]}}".format(var.unique_id))
            check.append(("hstep", ("humanstep", var.unique_id)))

            text.append("start: {{start[{}]}}".format(var.unique_id))
            check.append(("start", start[var.unique_id]))
            text.append("hstart: {{humanstart[{}]}}".format(var.unique_id))
            check.append(("hstart", self.formatVar(var, start[var.unique_id])))
            
            j = i
            text.append("series-start: {{series[{}][start]}}".format(j))
            check.append(("series-start", s["start"]))
            text.append("series-end: {{series[{}][end]}}".format(j))
            check.append(("series-end", s["end"]))
            text.append("series-width: {{series[{}][step-width]}}".format(j))
            check.append(("series-width", s["step-width"]))
            text.append("series-id: {{series[{}][variable]}}".format(j))
            check.append(("series-id", var.unique_id))
            text.append("hseries-start: {{humanseries[{}][start]}}".format(j))
            check.append(("hseries-start", self.formatVar(var, s["start"])))
            text.append("hseries-end: {{humanseries[{}][end]}}".format(j))
            check.append(("hseries-end", self.formatVar(var, s["end"])))
            text.append("hseries-width: {{humanseries[{}][step-width]}}".format(j))
            check.append(("hseries-width", self.formatVar(var, s["step-width"])))
            text.append("hseries-var: {{humanseries[{}][variable]}}".format(j))
            check.append(("hseries-var", name))
            
            if i + 1 < len(controller.microscope.supported_measurement_variables):
                s["on-each-point"] = {}
                s = s["on-each-point"]

        steps = pylo.MeasurementSteps(controller, start, series)
        counter = random.randint(0, len(steps) - 1)
        step = steps[counter]

        text.append("counter: {counter}")
        check.append(("counter", counter))

        time_format = "%Y%m%d%H%M"
        text.append("time: {{time:{}}}".format(time_format))
        check.append(("time", datetime.datetime.now().strftime(time_format)))
        
        tags = {
            "test 1": "Value",
            "group": {
                "test 2": 1,
                "test 3": False
            }
        }

        text.append("tag: {tags[test 1]}")
        check.append(("tag", tags["test 1"]))
        text.append("tag: {tags[group][test 2]}")
        check.append(("tag", tags["group"]["test 2"]))
        text.append("tag: {tags[group][test 3]}")
        check.append(("tag", tags["group"]["test 3"]))

        formatted_text = pylolib.expand_vars(*text, controller=controller, 
                                             step=step, start=start, 
                                             series=series, tags=tags, 
                                             counter=counter)

        print("step", step)
        print("start", start)
        print("series", series)
        print("tags", tags)
        print("counter", counter)
        print("check", check)
        print(formatted_text)
        
        for i, (name, val) in enumerate(check):
            if (isinstance(val, tuple) and len(val) == 2 and 
                val[0] in ("step", "humanstep")):
                if val[0] == "step":
                    val = step[val[1]]
                else:
                    var = controller.microscope.getMeasurementVariableById(val[1])
                    val = self.formatVar(var, step[val[1]])
            
            val = str(val)
            print("searching for",name, "with value", val)
            assert val in formatted_text[i]
    
    @pytest.mark.parametrize("text,expected", [
        ("A{?{keydoesnotexist} }B", "AB"),
        ("{?{keydoesnotexist}}", ""),
        ("{?A {keydoesnotexist} B}", ""),
        ("{_A {keydoesnotexist} B}", "A  B"),
        ("{_A {keydoesnotexist[index]} B}", "A  B")
    ])
    def test_expand_vars_ignore_missing(self, text, expected):
        assert expected == pylolib.expand_vars(text)[0]
    
    @pytest.mark.parametrize("text", [
        "A{!{keydoesnotexist}}B",
        "{!{keydoesnotexist}}",
        "{!A {keydoesnotexist} B}",
    ])
    def test_expand_vars_raise_error(self, text):
        with pytest.raises(KeyError):
            pylolib.expand_vars(text)
