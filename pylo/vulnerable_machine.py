import asyncio
import inspect
from .blocked_function_error import BlockedFunctionError
from .blocked_function import BlockedFunction
from .events import emergency

class VulnerableMachine:
    """
    An abstract class that allows machines to switch off if an error occurres.

    This object listens to the emergency event. If the emergency event is
    executed, the resetToEmergencyState() function is executed. Also the 
    emergency state will be saved until it is resolved again.

    Attributes
    ----------
    _in_emergency_state : bool
        Whether the current instrument is in emergency state at the moment, if 
        it is the user has to unblock everything manually
    """

    def __init__(self):
        """Create the vulnerable machine object"""
        self._in_emergency_state = False

        # add a listener to the emergency event to go in emergency state 
        # whenever the emergency event is created
        emergency.append(self.resetToEmergencyState)
    
    def resetToEmergencyState(self) -> None:
        """Set the machine to be in emergency state.

        This will reset the machine to be in the safe state. In addition the 
        emergency case will be saved. The user needs to unblock everything 
        until the program can continue.

        Calling this function will make all functions (except the 
        resolveEmergencyState() function) to throw a BlockedFunctionError.
        """

        self._in_emergency_state = True
        asyncio.run(self.resetToSafeState())

        for name, _ in inspect.getmembers(self, predicate=inspect.ismethod):
            if name != "resolveEmergencyState":
                setattr(self, name, BlockedFunction(getattr(self, name), name))
    
    def resolveEmergencyState(self) -> None:
        """Unblocks the machine and resolves the emergency state.

        The functions can now be used again.
        """
        for name, _ in inspect.getmembers(self, predicate=lambda x: isinstance(x, BlockedFunction)):
            setattr(self, name, getattr(self, name).func)
    
    async def resetToSafeState(self) -> None:
        """Set the machine into its safe state.

        The safe state will be used whenever something bad happens or when the 
        measurement has finished. The machine will be told to go in the safe 
        state. This should be a state where the machine can stay for long 
        times until the operator comes again.
        """
        raise NotImplementedError()