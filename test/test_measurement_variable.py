import math
import pytest
import random
import string

import pylo

class TestMeasurementVariable:
    def randomIdAndName(self):
        """Get a random id and a random name

        Returns
        -------
        str, str
            The id and the name
        """
        return (
            "".join(random.choice(string.ascii_lowercase) for i in range(5)),
            "".join(random.choice(string.ascii_lowercase) for i in range(15))
        )

    def test_no_optionals(self):
        """Test different construtor args."""
        var = pylo.MeasurementVariable("id", "name")

        assert var.unique_id == "id" and var.name == "name"

    def test_one_optional(self):
        """Test different construtor args."""
        var = pylo.MeasurementVariable("id", "name", 3)

        assert (var.unique_id == "id" and var.name == "name" and 
                var.min_value == 3 and var.max_value == None and 
                var.unit == None)

    def test_one_optional2(self):
        """Test different construtor args."""
        var = pylo.MeasurementVariable("id", "name", unit="N/mm^2")

        assert (var.unique_id == "id" and var.name == "name" and
                var.min_value == None and var.max_value == None and 
                var.unit == "N/mm^2")

    def test_tow_optionals(self):
        """Test different construtor args."""
        var = pylo.MeasurementVariable("id", "name", max_value=3, unit="N/mm^2")

        assert (var.unique_id == "id" and var.name == "name" and 
                var.min_value == None and var.max_value == 3 and 
                var.unit == "N/mm^2")

    def test_random_values(self):
        """Test if randomly generated MeasurementVariables work."""
        id_, name = self.randomIdAndName()

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

        var = pylo.MeasurementVariable(id_, name, min_value, max_value, unit)

        assert (var.unique_id == id_ and var.name == name and 
                var.min_value == min_value and var.max_value == max_value and 
                var.unit == unit)

    @pytest.mark.parametrize("calibration,uncalibration,test_calibrated,test_uncalibrated", [
        (2, None, 10, 5),
        (None, 0.5, 10, 5),
        (2, 0.5, 10, 5),
        # test ignoring invalid values if there is a number given
        (2, "invalid", 10, 5),
        ("invalid", 0.5, 10, 5),
        # ignore uncalibration if calibration is given
        (2, 100, 10, 5),
        # test callable
        (lambda x: x**2 + 1, lambda x: math.sqrt(x - 1), 26, 5)
    ])
    def test_valid_calibration(self, calibration, uncalibration, test_calibrated, test_uncalibrated):
        """Test if the calibration works for valid calibrations."""
        id_, name = self.randomIdAndName()
        
        if calibration is not None and uncalibration is not None:
            var = pylo.MeasurementVariable(
                id_, name, calibration=calibration, uncalibration=uncalibration
            )
        elif calibration is not None:
            var = pylo.MeasurementVariable(id_, name, calibration=calibration)
        elif uncalibration is not None:
            var = pylo.MeasurementVariable(id_, name, uncalibration=uncalibration)
        
        assert var.has_calibration

        assert var.convertToCalibrated(test_uncalibrated) == test_calibrated
        assert var.convertToUncalibrated(test_calibrated) == test_uncalibrated
    
    @pytest.mark.parametrize("calibration,uncalibration", [
        (26, lambda x: math.sqrt(x - 1)),
        (lambda x: x**2 + 1, 5),
        ("invalid", "invalid")
    ])
    def test_invalid_calibration(self, calibration, uncalibration):
        """Test invalid calibrations."""
        id_, name = self.randomIdAndName()

        with pytest.raises((TypeError, ValueError)):
            pylo.MeasurementVariable(
                id_, name, calibration=calibration, uncalibration=uncalibration
            )

    @pytest.mark.parametrize("min_value,max_value,calibration,uncalibration,calibrated_min,calibrated_max,expected_min,expected_max", [
        # calibrated min/max are more/less than uncalibrated ones
        (0, 10, 2, 0.5, 4, 16, 2, 8),
        # calibrated min/max are NOT more/less than uncalibrated ones
        (2, 8, 2, 0.5, 2, 18, 2, 8),
        # leave out
        (3, None, 3, None, None, 18, 3, 6),
        (None, 6, None, 1/3, 9, None, 3, 6),
        # only uncalibrated
        (None, None, lambda x: x**2, lambda x: math.sqrt(x), 4, 25, 2, 5)
    ])
    def test_calibrated_min_max(self, min_value, max_value, calibration, uncalibration, calibrated_min, calibrated_max, expected_min, expected_max):
        """Test the calibrated_min and calibrated_max values."""
        id_, name = self.randomIdAndName()

        args = {
            "calibration": calibration,
            "uncalibration": uncalibration
        }

        if min_value is not None:
            args["min_value"] = min_value
        if max_value is not None:
            args["max_value"] = max_value
        
        if calibrated_min is not None:
            args["calibrated_min"] = calibrated_min
        if calibrated_max is not None:
            args["calibrated_max"] = calibrated_max
        
        var = pylo.MeasurementVariable(id_, name, **args)

        assert var.min_value == expected_min
        assert var.max_value == expected_max
    
    @pytest.mark.parametrize("format", [
        int, 
        float, 
        bool, 
        lambda x: str(x * 100) + "%",
        pylo.Datatype(
            "is-a-type", 
            lambda x: "is a" if x == "a" else "not a", 
            lambda x: x == "a"
        )
    ])
    def test_format(self, format):
        """Test if a format is always converted to a Datatype or a type."""
        id_, name = self.randomIdAndName()

        var = pylo.MeasurementVariable(id_, name, format=format)

        assert isinstance(var.format, (type, pylo.Datatype))
