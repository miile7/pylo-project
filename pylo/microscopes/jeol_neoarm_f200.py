import threading
import time

import PyJEM.offline.TEM3 as TEM3

from .microscope_interface import MicroscopeInterface
from ..measurement_variable import MeasurementVariable

# the stage position constants in TEM3.stage3
STATE_INDEX_X_POS = 0
STATE_INDEX_Y_POS = 1
STATE_INDEX_Z_POS = 2
STATE_INDEX_X_TILT = 3
STATE_INDEX_Y_TILT = 4

# the stage status constants in TEM3.stage3
STAGE_STATUS_REST = 0
STAGE_STATUS_MOVING = 1
STAGE_STATUS_HARDWARE_LIMIT_ERROR = 2

# the lense ids for the free lense control in TEM3.lens3
CL1_LENSE_ID = 0
CL2_LENSE_ID = 1
CL3_LENSE_ID = 2
CM_LENSE_ID = 3
# reserved = 4
# reserved = 5
OL_COARSE_LENSE_ID = 6
OL_FINE_LENSE_ID = 7
OM1_LENSE_ID = 8
OM2_LENSE_ID = 9
IL1_LENSE_ID = 10
IL2_LENSE_ID = 11
IL3_LENSE_ID = 12
IL4_LENSE_ID = 13
PL1_LENSE_ID = 14
PL2_LENSE_ID = 15
PL3_LENSE_ID = 16
# reserved = 17
# reserved = 18
FL_COARSE_LENSE_ID = 19
FL_FINE_LENSE_ID = 20
FL_RATIO_LENSE_ID = 21
# reserved = 22
# reserved = 23
# reserved = 24
# reserved = 25

class JEOLNeoARMF200(MicroscopeInterface):
    """This class is the interface for communicating with the JEOL NeoARM F200
    TEM.

    For interaction with the Microscope this uses the JEOL PyJEM module. The 
    following values can be useful:
    - TEM3.lens3: There are getters and setters for the following lenses:
      - CL1 - CL3: Condenser Lenses?
      - CM: Condenser Mini Lense?
      - FL: ?
        - FLc: coarse value
        - FLf: fine value
        - FLcomp1, FLcomp2: Compo1 and compo2 value
      - IL1 - IL4: Intermediate Lense?
      - OL: Objective Lense
        - SuperFineSw: Super fine status (0 = Off, 1 = On)
        - SuperFineValue: Super fine value
        - OLc: coarse value
        - OLf: fine value
      - OM, OM2: Objective Mini lense
      - PL1 - PL3: Projection Lense
      - DiffFocus: ?
      - FLC: Free lense control, can be on and off for individual leses

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

        self._lense_control = TEM3.lens3.Lens3()
        self._stage = TEM3.stage3.Stage3()
        self._action_lock = threading.Lock()
    
    def setInLorenzMode(self, lorenz_mode : bool) -> None:
        """Set the microscope to be in lorenz mode.

        This disables the objective lense (OL)
        """

        # make sure only this function is currently using the microscope,
        # otherwise two functions may change microscope values at the same time
        # which will mess up things
        self._action_lock.acquire()

        if self._stage.GetHolderStts() == 0:
            raise IOError("The holder is not inserted.")

        if lorenz_mode:
            # endable free lense control for objective fine and coarse lense
            self._lense_control.SetFLCSw(OL_FINE_LENSE_ID, 1)
            self._lense_control.SetFLCSw(OL_COARSE_LENSE_ID, 1)

            # switch off fine and coarse objective lense
            self._lense_control.SetOLc(0)
            self._lense_control.SetOLf(0)
        else:
            # disable free lense control for objective fine and coarse lense
            self._lense_control.SetFLCSw(OL_FINE_LENSE_ID, 0)
            self._lense_control.SetFLCSw(OL_COARSE_LENSE_ID, 0)

        # let other functions access the microscope
        self._action_lock.release()
    
    def getInLorenzMode(self) -> bool:
        """Get whether the microscope is in the lorenz mode.

        This will return true if the objective fine and coarse lenses are 
        switched to free lense control and their current is 0.
        """

        # also for getting lock the microscope, just to be sure
        self._action_lock.acquire()
        
        lorenz_mode = (self._lense_control.GetFLCInfo(OL_FINE_LENSE_ID) == 1 and
                       self._lense_control.GetFLCInfo(OL_COARSE_LENSE_ID) == 1 and 
                       self._lense_control.GetOLc() == 0 and 
                       self._lense_control.GetOLf() == 0)
        
        # let other functions access the microscope
        self._action_lock.release()

        return lorenz_mode
    
    def setMeasurementVariableValue(self, id_, value):
        """Set the measurement variable."""
        
        if not self.isValidMeasurementVariableValue(id_, value):
            raise ValueError(("Either the id {} does not exist or the value " + 
                              "{} is not valid for the measurement " + 
                             "variable.").format(id_, value))
        elif id_ == "focus":
            self.setFocus(value)
        elif id_ == "magnetic-field":
            self.setMagneticField(value)
        elif id_ == "x-tilt":
            self.setXTilt(value)
        elif id_ == "y-tilt": 
            self.setYTilt(value)
        else:
            # this cannot happen, if the id doesn't exist the 
            # MicroscopeInterface::isValidMeasurementVariableValue returns 
            # false
            raise ValueError("The id {} does not exist.".format(id_))
    
    def setFocus(self, value):
        self._action_lock.acquire()

        self._action_lock.release()

    def setMagneticField(self, value):
        pass
    
    def setXTilt(self, value):
        # lock the microscope
        self._action_lock.acquire()

        # tell it to move to the given x angle
        self._stage.SetTiltXAngle(value)

        # wait until the x tilt has the desired value
        while self._stage.GetStatus()[STATE_INDEX_X_TILT] == STAGE_STATUS_MOVING:
            time.sleep(0.1)

        # allow other functions to use the microscope
        self._action_lock.release()

    def setYTilt(self, value):
        pass

    def resetToSafeState(self):
        # lock the microscope
        self._action_lock.acquire()

        # set the stage to the original position
        self._stage.SetOrg()
        self._action_lock.release()


# make sure to somehow save when a measurement variable is set, in the setsafemode
# wait until the measurement variable is set successfully, then set the 
# safe mode, use threading.Lock or queue.SimpleQueue