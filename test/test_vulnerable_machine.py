if __name__ == "__main__":
    # For direct call only
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import pylo

class DummyMachine(pylo.VulnerableMachine):
    def __init__(self):
        self.is_in_safe_state = False
        super().__init__()
    
    def test_function(self) -> bool:
        return True
    
    def resetToSafeState(self) -> None:
        self.is_in_safe_state = True

class TestVulnerableMachine:
    @pytest.fixture(autouse=True)
    def clear_event_handlers_and_delete_machine(self):
        # clear event handlers
        pylo.emergency.clear()

        machine = DummyMachine()
        yield 

        # remove the machine, otherwise the machine will not be deleted by the 
        # garbage collector because there is an instance in the event handler
        del machine

    def test_emergency_state(self):
        """Test if the machine goes in the emergency state if 
        resetToEmergencyState() is executed
        """
        machine = DummyMachine()
        machine.resetToEmergencyState()

        assert machine._in_emergency_state == True

    def test_emergency_state_safe(self):
        """Test if the machine goes in the safe state if 
        resetToEmergencyState() is executed
        """
        machine = DummyMachine()
        machine.resetToEmergencyState()

        assert machine.is_in_safe_state == True

    def test_emergency_state_function_before(self):
        """Check if functions can be executed by default"""
        machine = DummyMachine()

        assert machine.test_function() == True

    def test_emergency_state_function_wile(self):
        """Test if functions can be executed while the machine is in emergency 
        state
        """
        machine = DummyMachine()
        machine.resetToEmergencyState()

        with pytest.raises(pylo.BlockedFunctionError):
            machine.test_function()

    def test_emergency_state_function_after(self):
        """Test if functions can be executed after the machine was in emergency 
        state and is then resolved
        """
        machine = DummyMachine()
        machine.resetToEmergencyState()
        machine.resolveEmergencyState()

        assert machine.test_function() == True

    def test_emergency_state_after(self):
        """Test if the machine is not in emergency mode after resolving the 
        emergency state.
        """
        machine = DummyMachine()
        machine.resetToEmergencyState()
        machine.resolveEmergencyState()

        assert machine._in_emergency_state == True

    def test_emergency_state_by_event(self):
        """Test if the machine goes in emergency mode if the emergency event 
        is fired
        """
        machine = DummyMachine()
        pylo.emergency()

        assert machine._in_emergency_state == True

    def test_emergency_state_safe_by_event(self):
        """Test if the machine goes in safe state if the emergency event 
        is fired
        """
        machine = DummyMachine()
        pylo.emergency()

        assert machine.is_in_safe_state == True

    def test_emergency_state_function_wile_by_event(self):
        """Test if functions can be executed while the machine is in emergency 
        state triggered by the emergency event
        """
        machine = DummyMachine()
        pylo.emergency()

        with pytest.raises(pylo.BlockedFunctionError):
            machine.test_function()

if __name__ == "__main__":
    t = TestVulnerableMachine()
    t.test_emergency_state_by_event()
    t.test_emergency_state_safe_by_event()