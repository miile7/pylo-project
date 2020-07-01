from .microscope_interface import MicroscopeInterface
from ..measurement_variable import MeasurementVariable

class JEOLNeoARMF200(MicroscopeInterface):
    """This class is the interface for communicating with the JEOL NeoARM F200
    TEM.
    """
    
    def __init__(self):
        """Get the microscope instance"""
        super().__init__()

        # set all measurement variables sequential, not parallel
        self.supports_parallel_measurement_variable_setting = False

        self.supported_measurement_variables = [
            MeasurementVariable("focus", "Focus", 0, 1, "hex"),
            MeasurementVariable("ol-current", "Objective lense current", 0, 1, "hex"),
            MeasurementVariable("x-tilt", "X Tilt", -10, 10, "deg"),
            MeasurementVariable("y-tilt", "Y Tilt", -10, 10, "deg"),
        ]

# make sure to somehow save when a measurement variable is set, in the setsafemode
# wait until the measurement variable is set successfully, then set the 
# safe mode, use threading.Lock or queue.SimpleQueue