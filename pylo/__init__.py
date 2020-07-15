"""A python module to do magnetic measuremnets in the Lorenz-Mode with TEMs.

This provides both, the GUI and the backend for measuring. Multiple GUIs are 
offered together with various cameras and TEM implementations.
"""

class __Docs(list):
    """A class for creating the docstring easily."""
    def __call__(self, name, text):
        self.append((name, text))
    
    def __str__(self):
        return "\n\n".join(["{}:\n{}".format(n, t) for n, t in self])

__doc__ += "\n\nConfiguration (.config)\n-----------------------\n"
__doc__ += """The following configurations are set in the config. They contain
the default values for the attributes that have to be known before the 
configuration object is loaded. In additions some default values for the 
configuration object are set here. This should only be modified when installing
the program once.\n\n"""
from .config import __config_docs__
__doc__ += str(__config_docs__)

from .event import Event
from .events import emergency
from .events import after_stop
from .events import before_start
from .events import before_init
from .events import init_ready
from .events import user_ready
from .events import series_ready
from .events import microscope_ready
from .events import before_record
from .events import after_record
from .events import measurement_ready

__doc__ += "\n\nEvents (.events)\n----------------\n"
__doc__ += """The following events are available after the program starts. You 
can add any kind of callable which will be executed when the event is fired.\n\n"""
from .events import __event_docs__
__doc__ += str(__event_docs__)

from .image import Image
from .controller import Controller
from .measurement import Measurement
from .stop_program import StopProgram
from .abstract_view import AbstractView
from .exception_thread import ExceptionThread
from .blocked_function import BlockedFunction
from .vulnerable_machine import VulnerableMachine
from .measurement_variable import MeasurementVariable
from .blocked_function_error import BlockedFunctionError
from .abstract_configuration import AbstractConfiguration

controller = None

def get_controller() -> Controller:
    """Get the current instance of the controller.

    Returns
    -------
    Controller
        The current controller
    """

    global controller
    if controller is None or not isinstance(controller, Controller):
        controller = Controller()
    
    return controller

def setup() -> Controller:
    """Create the setup for the measurement.
    
    Returns
    -------
    Controller
        The current controller
    """
    
    return get_controller()

def start() -> Controller:
    """Start the measurement.

    The measurement is started in another thread, so it will run in the 
    background. To wait for the measurement to finish use the `execute()`
    function.
    
    Returns
    -------
    Controller
        The current controller
    """
    
    controller = setup()
    controller.startProgramLoop()

    return controller

def execute() -> Controller:
    """Start the measurement and wait until it has finished.

    To execute the measurement in another thread without waiting for it to 
    finish use the `start()` function.
    
    Returns
    -------
    Controller
        The current controller
    """

    controller = start()
    controller.waitForProgram()

    return controller