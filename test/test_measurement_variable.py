import pytest
import random
import string

from pylo.measurement_varibale import MeasurementVariable

class TestMeasurementVariable:
    def test_no_optionals(self):
        var = MeasurementVariable("id", "name")

        assert var.unique_id == "id" and var.name == "name"

    def test_one_optional(self):
        var = MeasurementVariable("id", "name", 3)

        assert (var.unique_id == "id" and var.name == "name" and 
                var.min_value == 3 and var.max_value == None and 
                var.unit == None)

    def test_one_optional2(self):
        var = MeasurementVariable("id", "name", unit="N/mm^2")

        assert (var.unique_id == "id" and var.name == "name" and
                var.min_value == None and var.max_value == None and 
                var.unit == "N/mm^2")

    def test_tow_optionals(self):
        var = MeasurementVariable("id", "name", max_value=3, unit="N/mm^2")

        assert (var.unique_id == "id" and var.name == "name" and 
                var.min_value == None and var.max_value == 3 and 
                var.unit == "N/mm^2")

    def test_random_values(self):
        id_ = "".join(random.choice(string.ascii_lowercase) for i in range(5))
        name = "".join(random.choice(string.ascii_lowercase) for i in range(15))

        if random.random() >= 0.5:
            min_value = random.randint(0, 10)
        else:
            min_value = None

        if random.random() >= 0.5:
            max_value = random.randint(10, 20)
        else:
            max_value = None

        if random.random() >= 0.5:
            unit = "".join(random.choice(string.ascii_lowercase) for i in range(5))
        else:
            unit = None

        var = MeasurementVariable(id_, name, min_value, max_value, unit)

        assert (var.unique_id == id_ and var.name == name and 
                var.min_value == min_value and var.max_value == max_value and 
                var.unit == unit)
