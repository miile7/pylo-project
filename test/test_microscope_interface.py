import unittest
import asyncio
import pylo.microscopes
# import pylo.MeasurementVariable

class TestMicroscopeInterface(unittest.TestCase):
    def test_error_is_thrown(self):
        microscope = pylo.microscopes.MicroscopeInterface()

        with self.assertRaises(NotImplementedError):
            asyncio.run(microscope.setInLorenzMode(True))
        
        with self.assertRaises(NotImplementedError):
            asyncio.run(microscope.getInLorenzMode())
        
        with self.assertRaises(NotImplementedError):
            asyncio.run(microscope.setMeasurementVariableValue("test-variable", 0))
        
        with self.assertRaises(NotImplementedError):
            asyncio.run(microscope.getMeasurementVariableValue("test-variable"))
        
        with self.assertRaises(NotImplementedError):
            asyncio.run(microscope.resetToSafeState())
        
    # def test_is_valid_measurement_variable_value(self):
    #     microscope = pylo.microscopes.MicroscopeInterface()
    #     microscope.supported_measurement_variables.append(
    #         pylo.MeasurementVariable()
    #     )
    #     microscope.isValidMeasurementVariableValue("test-variable", 0)