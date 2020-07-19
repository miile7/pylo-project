import pytest
import pylo.microscopes
import pylo

class TestMicroscopeInterface:
    def setup_method(self, method):
        self.microscope = pylo.microscopes.MicroscopeInterface()
        self.microscope.supported_measurement_variables.append(
            pylo.MeasurementVariable("test-var-1", "Test Variable 1", 0, 10, "ut")
        )
        self.microscope.supported_measurement_variables.append(
            pylo.MeasurementVariable("test-var-2", "Test Variable 2", max_value=100)
        )
        self.microscope.supported_measurement_variables.append(
            pylo.MeasurementVariable("test-var-3", "Test Variable 3", min_value=1)
        )

    def test_error_is_thrown_set_lorenz_mode(self):
        with pytest.raises(NotImplementedError):
            self.microscope.setInLorenzMode(True)
        
    def test_error_is_thrown_get_lorenz_mode(self):
        with pytest.raises(NotImplementedError):
            self.microscope.getInLorenzMode()
        
    def test_error_is_thrown_set_measurement_variable(self):
        with pytest.raises(NotImplementedError):
            self.microscope.setMeasurementVariableValue("test-variable", 0)
        
    def test_error_is_thrown_get_measurement_variable(self):
        with pytest.raises(NotImplementedError):
            self.microscope.getMeasurementVariableValue("test-variable")
        
    def test_error_is_thrown_reset_to_safe_state(self):
        with pytest.raises(NotImplementedError):
            self.microscope.resetToSafeState()

    @pytest.mark.parametrize("id_,value", [
        ("test-var-1", 0),
        ("test-var-1", 6),
        ("test-var-1", 8.983289),
        ("test-var-1", 10),
        ("test-var-2", 82.1),
        ("test-var-2", 100),
        ("test-var-3", 1),
        ("test-var-3", 2),
    ])
    def test_is_valid_measurement_variable_value(self, id_, value):
        assert self.microscope.isValidMeasurementVariableValue(id_, value) == True

    @pytest.mark.parametrize("id_,value", [
        ("test-var-1", 11),
        ("test-var-1", -1),
        ("test-var-1", float("inf")),
        ("test-var-1", -float("inf")),
        ("test-var-2", 100.0000000001),
        ("test-var-3", 0.999),
        ("variable-doesnt-exist", 2),
        ("test-var-1", "wrong-type")
    ])
    def test_is_invalid_measurement_variable_value(self, id_, value):
        assert self.microscope.isValidMeasurementVariableValue(id_, value) == False