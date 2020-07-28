import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
import pytest
import math

import pylo
import pylo.config

pylo.config.CONFIGURATION = pylo.AbstractConfiguration()
controller = pylo.Controller()

###############################################################################
###                                                                         ###
###         Change only this for testing a different microscope             ###
###                                                                         ###
###############################################################################

# How to use
# **********
#
# 1. Create a new function `create_your_microscope()` that returns your 
#    microscope object instance
# 2. Add your `create_your_microscope()` to the configurations tuple
# 
# For an example check the commented code below.

# def create_your_microscope() -> plyo.microscopes.MicroscopeInterface
#     return plyo.MicroscopeInterface()

def create_pyjem_microscope() -> pylo.microscopes.MicroscopeInterface:
    microscope = pylo.microscopes.PyJEMMicroscope(controller)
    controller.microscope = microscope
    return microscope

microscopes = (
    # create_your_microscope,
    create_pyjem_microscope, 
)

######################## general test code starts here ########################

class TestPyJEMMicroscope:
    @pytest.mark.parametrize("microscope", microscopes)
    def test_lorenz_mode(self, microscope):
        """Test if the lorenz mode works."""

        microscope = microscope()

        microscope.setInLorenzMode(True)

        assert microscope.getInLorenzMode()
    
    @pytest.mark.parametrize("microscope", microscopes)
    def test_measurement_variables(self, microscope):
        """Test if all vairables can be set and if the get value is equal to
        the set value."""

        microscope = microscope()

        for var in microscope.supported_measurement_variables:
            values = []
            if isinstance(var.min_value, (int, float)):
                values.append(var.min_value)
            if isinstance(var.max_value, (int, float)):
                values.append(var.max_value)
            
            if len(values) == 0:
                values.append(random.randint(0, 10))
            
            for val in values:
                microscope.setMeasurementVariableValue(var.unique_id, val)

                assert (microscope.getMeasurementVariableValue(var.unique_id) == val)
    
    @pytest.mark.parametrize("microscope", microscopes)
    def test_save_state(self, microscope):
        """Test if the getCurrentState() and setCurrentState() work properly."""

        microscope = microscope()

        if (not hasattr(microscope, "getCurrentState") or 
            not callable(microscope.getCurrentState) or 
            not hasattr(microscope, "setCurrentState") or 
            not callable(microscope.setCurrentState)):
            pytest.skip("The microscope does not have the getCurrentState() " + 
                        "or the setCurrentState() function so it cannot be " + 
                        "tested.")

        # save state
        state = microscope.getCurrentState()
        
        # set some random values to the measurement variables
        for var in microscope.supported_measurement_variables:
            lower = None
            upper = None
            if isinstance(var.min_value, (int, float)):
                lower = var.min_value
            if isinstance(var.max_value, (int, float)):
                upper = var.max_value
            
            if lower is None and upper is None:
                # use random values
                lower = 0
                upper = 100
            elif lower is None and upper is not None:
                if upper > 0:
                    lower = 0
                else:
                    lower = upper - 100
            elif lower is not None and upper is None:
                if lower < 100:
                    upper = 100
                else:
                    upper = lower + 100
            
            if math.floor(lower) == math.floor(upper):
                val = random.uniform(lower, upper)
            else:
                val = random.randint(lower, upper)
            
            microscope.setMeasurementVariableValue(var.unique_id, val)
        
        # reset to the initial state
        microscope.setCurrentState(state)

        # check if the new state is equal to the initial state
        assert microscope.getCurrentState() == state
    
    @pytest.mark.parametrize("microscope", microscopes)
    def test_reset_to_safe_state(self, microscope):
        """Test if there is no error in the safe state. Note that this does not
        check if the safe state is actually occupied. This will only execute 
        the function to check if there are no python errors in the code."""

        microscope = microscope()
        microscope.resetToSafeState()
    
    @pytest.mark.parametrize("microscope", microscopes)
    def test_reset_to_emergency_state(self, microscope):
        """Test if there is no error in the emergency state. Note that this 
        does not check if the safe state is actually occupied. This will only 
        execute the function to check if there are no python errors in the code.
        """

        microscope = microscope()
        microscope.resetToEmergencyState()