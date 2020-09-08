__file__ = ""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

print(sys.path)

import DigitalMicrograph as DM
import random
import dmtestlib

import pylo

class TestPyLoDMLib:
    @dmtestlib.parametrize("dmscript,variables", [
        ("number a, b, c;\n" + 
         "a = 5;\n" + 
         "b = 10;\n" + 
         "c = a + b;",
         {"c": "number"},
         {"c": 15})
    ])
    def test_variables(self, dmscript, variables, result_variables):
        with pylo.pylodmlib.executeDMScript(dmscript, variables) as script:
            for var_name, var_value in result_variables.items():
                if isinstance(var_value, (int, float)):
                    assert float(var_value) == float(script[var_name])
                else:
                    assert var_value == var_name