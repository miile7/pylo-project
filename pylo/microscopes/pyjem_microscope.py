import time
import typing
import threading

from ..config import OFFLINE_MODE
error = None
if OFFLINE_MODE != True:
    try:
        from PyJEM.TEM3 import Apt3
        from PyJEM.TEM3 import EOS3
        from PyJEM.TEM3 import FEG3
        from PyJEM.TEM3 import GUN3
        from PyJEM.TEM3 import Lens3
        from PyJEM.TEM3 import Stage3
    except ImportError as e:
        error = e
if OFFLINE_MODE == True or error is not None:
    from PyJEM.offline.TEM3.apt3 import Apt3
    from PyJEM.offline.TEM3.eos3 import EOS3
    from PyJEM.offline.TEM3.feg3 import FEG3
    from PyJEM.offline.TEM3.gun3 import GUN3
    from PyJEM.offline.TEM3.lens3 import Lens3
    from PyJEM.offline.TEM3.stage3 import Stage3

from ..datatype import Datatype
from .microscope_interface import MicroscopeInterface
from ..measurement_variable import MeasurementVariable

# the group name in the configuration for settings that are related to this
# microscope
CONFIG_PYJEM_MICROSCOPE_GROUP = "pyjem-microscope"

# the function modes for TEM mode
FUNCTION_MODE_TEM_MAG = 0
FUNCTION_MODE_TEM_MAG2 = 1
FUNCTION_MODE_TEM_LowMAG = 2
FUNCTION_MODE_TEM_SAMAG = 3
FUNCTION_MODE_TEM_DIFF = 4

# the function modes for STEM mode
FUNCTION_MODE_STEM_ALIGN = 0
FUNCTION_MODE_STEM_SM_LMAG = 1
FUNCTION_MODE_STEM_SM_MAG = 2
FUNCTION_MODE_STEM_AMAG = 3
FUNCTION_MODE_STEM_uuDIFF = 4
FUNCTION_MODE_STEM_ROCKING = 5

# the probe modes
PROBE_MODE_TEM = 0
PROBE_MODE_EDS = 1
PROBE_MODE_NBD = 2
PROBE_MODE_CBD = 3

# the stage position constants in TEM3.stage3
STAGE_INDEX_X_POS = 0
STAGE_INDEX_Y_POS = 1
STAGE_INDEX_Z_POS = 2
STAGE_INDEX_X_TILT = 3
STAGE_INDEX_Y_TILT = 4

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

class PyJEMMicroscope(MicroscopeInterface):
    """This class is the interface for communicating with the JEOL PyJEM 
    python interface.

    Most shortcuts are documented at the JEOL Glossary:
    https://www.jeol.co.jp/en/words/emterms/search_result.html?keyword=

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
    
    def __init__(self, controller : "Controller") -> None:
        """Get the microscope instance"""
        super().__init__(controller)

        # set all measurement variables sequential, not parallel
        self.supports_parallel_measurement_variable_setting = False

        try:
            magnetic_field_calibration_factor = (
                self.controller.configuration.getValue(
                    CONFIG_PYJEM_MICROSCOPE_GROUP, 
                    "objective-lense-magnetic-field-calibration"
                )
            )
        except KeyError:
            magnetic_field_calibration_factor = None
        
        try:
            magnetic_field_unit = (
                self.controller.configuration.getValue(
                    CONFIG_PYJEM_MICROSCOPE_GROUP, 
                    "magnetic-field-unit"
                )
            )
        except KeyError:
            magnetic_field_unit = None

        self.supported_measurement_variables = [
            # limits taken from 
            # PyJEM/doc/interface/TEM3.html#PyJEM.TEM3.EOS3.SetObjFocus
            MeasurementVariable("focus", "Focus", -1, 50),
            MeasurementVariable("x-tilt", "X Tilt", -10, 10, "deg"),
            MeasurementVariable("y-tilt", "Y Tilt", -10, 10, "deg"),
            MeasurementVariable(
                "om-current", 
                "Objective Mini Lense Current", 
                unit="hex",
                format=hex_int,
                min_value = 0x0,
                max_value = 0x1,
                calibrated_unit=magnetic_field_unit,
                calibrated_name="Magnetic Field",
                calibration=magnetic_field_calibration_factor,
                calibrated_format=float
            )
        ]

        # the lenses
        self._lense_control = Lens3()
        # the stage
        self._stage = Stage3()
        # Electron opcical system
        self._eos = EOS3()
        # ???
        self._feg = FEG3()
        # gun
        self._gun = GUN3()
        # the aperture
        self._aperture = Apt3()
        # a lock so only one action can be performed at once at the microscope
        self._action_lock = threading.Lock()

        # save current focus, there is no get function
        self._focus = 0
        # save the initial state to reset the microscope to this state in the 
        # end
        self._init_state = self.getCurrentState()
    
    def getCurrentState(self) -> dict:
        """Get the current state saved as a dict.

        This creates a dict that contains the values of some internal devices 
        to save the current microscope state.

        Currently this saves:
        - cl1: The CL1 value (condensor lense 1 current)
        - cl2: The CL2 value (condensor lense 2 current)
        - cl3: The CL3 value (condensor lense 3 current)
        - il1: The IL1 value (intermediate lense 1 current)
        - il2: The IL2 value (intermediate lense 2 current)
        - il3: The IL3 value (intermediate lense 3 current)
        - il4: The IL4 value (intermediate lense 4 current)
        - pl1: The PL1 value (projection lense 1 current)
        - pl2: The PL2 value (projection lense 2 current)
        - pl3: The PL3 value (projection lense 3 current)
        - probe-mode: The probe mode as a `PROBE_MODE_*` constant
        - function-mode: The probe mode as a `FUNCTION_MODE_*` constant

        Returns
        -------
        dict
            The state dict
        """

        state = {
            "cl1": self._lense_control.GetCL1(),
            "cl2": self._lense_control.GetCL2(),
            "cl3": self._lense_control.GetCL3(),
            "il1": self._lense_control.GetIL1(),
            "il2": self._lense_control.GetIL2(),
            "il3": self._lense_control.GetIL3(),
            "il4": self._lense_control.GetIL4(),
            "pl1": self._lense_control.GetPL1(),
            "pl2": self._lense_control.GetPL2(),
            "pl3": self._lense_control.GetPL3(),
            "probe-mode": self._eos.GetProbeMode(),
            "function-mode": self._eos.GetFunctionMode(),
        }

        return state
    
    def setCurrentState(self, state: dict, ignore_invalid_keys: typing.Optional[bool]=False) -> None:
        """Sets the `state`.

        The `state` is a dict that contains the value of an internal instrument
        with the corresponding key. Note that the values are NOT CHECKED! This 
        means they have to be valid and in the pyhsical bondaries of the 
        microscope!

        The `state` dict is described in the 
        `PyJEMMicroscope::getCurrentState()` function. Note that the `state` 
        does not have to contain all the keys.

        Raises
        ------ 
        KeyError
            When a key in the `state` is not known and `ignore_invalid_keys`
            is False

        Parameters
        ----------
        state : dict
            The state dict as returned by `PyJEMMicroscope::getCurrentState()`, 
            not all keys have to be given
        ignore_invalid_keys : bool, optional
            Whether to raise an error if a key is not known (True) or to ignore
            this key (False), default: False
        """

        for key, value in state.items():
            if key == "cl1": 
                self._lense_control.SetFLCAbs(CL1_LENSE_ID, value)
            elif key == "cl2": 
                self._lense_control.SetFLCAbs(CL2_LENSE_ID, value)
            elif key == "cl3": 
                self._lense_control.SetCL3(value)
            elif key == "il1": 
                self._lense_control.SetFLCAbs(IL1_LENSE_ID, value)
            elif key == "il2": 
                self._lense_control.SetFLCAbs(IL2_LENSE_ID, value)
            elif key == "il3": 
                self._lense_control.SetFLCAbs(IL3_LENSE_ID, value)
            elif key == "il4": 
                self._lense_control.SetFLCAbs(IL4_LENSE_ID, value)
            elif key == "pl1": 
                self._lense_control.SetFLCAbs(PL1_LENSE_ID, value)
            elif key == "pl2": 
                self._lense_control.SetFLCAbs(PL2_LENSE_ID, value)
            elif key == "pl3": 
                self._lense_control.SetFLCAbs(PL3_LENSE_ID, value)
            elif key == "probe-mode":
                self._eos.SelectProbMode(value)
            elif key == "function-mode":
                self._eos.SelectFunctionMode(value)
            elif not ignore_invalid_keys:
                raise KeyError("The key '{}' is invalid.".format(key))
    
    def setInLorenzMode(self, lorenz_mode : bool) -> None:
        """Set the microscope to be in lorenz mode.

        This sets the probe mode to *TEM* and the function mode to *LowMAG*. It
        disables the objective lense (OL fine and coarse) and sets them to 0.

        Raises
        ------
        IOError
            When there is no holder inserted.

        Parameters
        ----------
        lorenz_mode : bool
            Whether the microscope should be in lorenz mode or not
        """

        # make sure only this function is currently using the microscope,
        # otherwise two functions may change microscope values at the same time
        # which will mess up things
        self._action_lock.acquire()

        # if self._stage.GetHolderStts() == 0:
        #     raise IOError("The holder is not inserted.")

        if lorenz_mode:
            # select TEM mode
            self._eos.SelectProbMode(PROBE_MODE_TEM)
            # select low mag mode, this is the most important step because this
            # will re-arrange the lense currents and apply the focus using the 
            # objective mini lense
            self._eos.SelectFunctionMode(FUNCTION_MODE_TEM_LowMAG)

            # switch off fine and coarse objective lense, even though this is 
            # done by the low mag mode anyway
            self._lense_control.SetOLc(0)
            self._lense_control.SetOLf(0)

            # self._lense_control.SetOLSuperFineNeutral()

        else:
            # keep tem mode
            self._eos.SelectProbMode(PROBE_MODE_TEM)
            # select normal mag mode
            self._eos.SelectFunctionMode(FUNCTION_MODE_TEM_MAG)

            # set neutral?
            # self._lense_control.SetNtrl((Lens3)arg1, (int)arg2)
            # NTRL within only value range.
            # 0:Brightness, 1:OBJ Focus, 2:DIFF Focus, 3:IL Focus, 4:PL Focus, 5:FL Focus

        # let other functions access the microscope
        self._action_lock.release()
    
    def getInLorenzMode(self) -> bool:
        """Get whether the microscope is in the lorenz mode.

        This will return true if the objective fine and coarse lenses are 
        switched to free lense control and their current is 0.
        """

        # also for getting lock the microscope, just to be sure
        self._action_lock.acquire()
        
        lorenz_mode = (
            self._eos.GetProbeMode() == PROBE_MODE_TEM and 
            self._eos.GetFunctionMode() == FUNCTION_MODE_TEM_LowMAG
        )
        
        # let other functions access the microscope
        self._action_lock.release()

        return lorenz_mode
    
    def setMeasurementVariableValue(self, id_: str, value: float) -> None:
        """Set the measurement variable defined by its id to the given value in
        its specific units.

        Note it does not matter if a calibration is given or not. The 
        calibration is for visuals (in the GUI and the saved values) only. So
        **the `value` is the uncalibrated value**. It will NOT be 
        re-calculated!

        The JEOL NeoARM F200 supports the following variables:
        - 'focus': The focus current in ?
        - 'om-current': The objective lense current which induces a magnetic 
          field or the magnetic field itself
        - 'x-tilt': The tilt in x direction in degrees
        - 'y-tilt': The tilt in y direction in degrees, only supported if the 
          correct probe holder is installed

        Raises
        ------
        ValueError
            When there is no measurement variable with the given id or when the 
            `value` is out of its bounds.

        Parameters
        ----------
        id_ : str
            The id of the measurement variable
        value : float
            The value to set in the specific units
        """
        
        if not self.isValidMeasurementVariableValue(id_, value):
            raise ValueError(("Either the id {} does not exist or the value " + 
                              "{} is not valid for the measurement " + 
                              "variable.").format(id_, value))

        elif id_ == "focus":
            self._setFocus(value)
        elif id_ == "om-current":
            self._setObjectiveLenseCurrent(value)
        elif id_ == "x-tilt":
            self._setXTilt(value)
        elif id_ == "y-tilt": 
            self._setYTilt(value)
        else:
            # this cannot happen, if the id doesn't exist the 
            # MicroscopeInterface::isValidMeasurementVariableValue returns 
            # false
            raise ValueError("The id {} does not exist.".format(id_))
    
    def _setFocus(self, value : float) -> None:
        """Set the focus to the given value.

        Typical values are between -1 and 50.

        Parameters
        ----------
        value : float
            The focus value
        """
        
        diff = value - self._focus
        self._action_lock.acquire()
        self._eos.SetObjFocus(diff)
        # self._eos.SetDiffFocus(value) +-1 to 50
        # self._lense_control.SetDiffFocus(value) +-1 to 50
        # self._lense_control.SetILFocus(value)
        # self._lense_control.SetPLFocus(value)
        self._focus = value
        self._action_lock.release()

    def _setObjectiveLenseCurrent(self, value : float) -> None:
        """Set the objective lense current.

        The value corresponds to I/O output value without carry.

        This function blocks the `PyJEMMicroscope::_action_lock`
        
        Parameters
        ----------
        value : int or float
            The value to set the objective lense current to.
        """

        if not self.isValidMeasurementVariableValue("om-current", value):
            raise ValueError(("The value {} is not allowed for the " + 
                              "objective lense current.").format(value))
        
        # lock the microscope
        self._action_lock.acquire()

        # self._lense_control.SetOLc(value // self.objective_lense_coarse_solution)
        # self._lense_control.SetOLf(value % self.objective_lense_coarse_solution)
        self._lense_control.SetOLf(value)

        # allow other functions to use the microscope
        self._action_lock.release()
    
    def _setXTilt(self, value : float) -> None:
        """Set the x tilt in degrees.

        This function blocks the `PyJEMMicroscope::_action_lock`. It will 
        execute until the x tilt is set correctly.
        
        Parameters
        ----------
        value : int or float
            The value to set the x tilt in degrees.
        """

        if not self.isValidMeasurementVariableValue("x-tilt", value):
            raise ValueError(("The value {} is not allowed for the " + 
                              "x tilt.").format(value))
        
        # lock the microscope
        self._action_lock.acquire()

        # tell it to move to the given x angle
        self._stage.SetTiltXAngle(value)

        # wait until the x tilt has the desired value
        while self._stage.GetStatus()[STAGE_INDEX_X_TILT] == STAGE_STATUS_MOVING:
            time.sleep(0.1)

        # allow other functions to use the microscope
        self._action_lock.release()

    def _setYTilt(self, value : float) -> None:
        """Set the y tilt in degrees.

        This function blocks the `PyJEMMicroscope::_action_lock`. It will 
        execute until the y tilt is set correctly.

        Note that not all probe holders support a y tilt!
        
        Parameters
        ----------
        value : int or float
            The value to set the y tilt in degrees.
        """

        if not self.isValidMeasurementVariableValue("y-tilt", value):
            raise ValueError(("The value {} is not allowed for the " + 
                              "y tilt.").format(value))
        
        # lock the microscope
        self._action_lock.acquire()

        # tell it to move to the given y angle
        self._stage.SetTiltYAngle(value)

        # wait until the y tilt has the desired value
        while self._stage.GetStatus()[STAGE_INDEX_Y_TILT] == STAGE_STATUS_MOVING:
            time.sleep(0.1)

        # allow other functions to use the microscope
        self._action_lock.release()
    
    def getMeasurementVariableValue(self, id_: str) -> float:
        """Get the value for the given `MeasurementVariable` id.

        Note it does not matter if a calibration is given or not. The 
        calibration is for visuals (in the GUI and the saved values) only. So
        **the return value is the uncalibrated value**. It will NOT be 
        re-calculated!

        Raises
        ------
        ValueError
            When there is no `MeasurementVariable` for the `id_`.
        """

        if id_ == "focus":
            value = self._getFocus()
        elif id_ == "om-current":
            value = self._getObjectiveLenseCurrent()
        elif id_ == "x-tilt":
            value = self._getXTilt()
        elif id_ == "y-tilt":
            value = self._getYTilt()
        else:
            raise ValueError(("There is no MeasurementVariable for the " + 
                              "id {}.").format(id_))
        
        return value
    
    def _getFocus(self) -> float:
        """Get the current focus as an absolute value.

        Note that this is the only value that cannot be received from the 
        microscope. To get the absolute value, the focus is saved internally 
        by adding the differences.

        Returns
        -------
        float
            The focus
        """
        # self._action_lock.acquire()

        # GetObjFocus() doesn't exist, no idea how to get the focus value 
        # (except for saving it but that is only the last escape, this makes it
        # impossible to check if the focus really is set correctly)
        # self._eos.GetObjFocus()

        # self._action_lock.release()
        return self._focus
    
    def _getObjectiveLenseCurrent(self) -> float:
        """Get the objective lense current in the current units.

        Returns
        -------
        float
            The actual current of the objective lense at the microscope
        """

        # lock the microscope
        self._action_lock.acquire()

        value = (
            self._lense_control.GetOLf() + 0
            # self._lense_control.GetOLf() * self.objective_lense_coarse_solution
        )

        # allow other functions to use the microscope
        self._action_lock.release()

        return value
    
    def _getXTilt(self) -> float:
        """Get the x tilt in degrees.

        Returns
        -------
        float
            The x tilt
        """

        # lock the microscope
        self._action_lock.acquire()

        # wait until the x tilt is not changing anymore
        while self._stage.GetStatus()[STAGE_INDEX_X_TILT] == STAGE_STATUS_MOVING:
            time.sleep(0.1)

        # get the current stage position (includes the tilt)
        pos = self._stage.GetPos()

        # allow other functions to use the microscope
        self._action_lock.release()

        return pos[STAGE_INDEX_X_TILT]
    
    def _getYTilt(self) -> float:
        """Get the y tilt in degrees.

        Returns
        -------
        float
            The y tilt
        """
        
        # lock the microscope
        self._action_lock.acquire()

        # wait until the y tilt is not changing anymore
        while self._stage.GetStatus()[STAGE_INDEX_Y_TILT] == STAGE_STATUS_MOVING:
            time.sleep(0.1)

        # get the current stage position (includes the tilt)
        pos = self._stage.GetPos()

        # allow other functions to use the microscope
        self._action_lock.release()

        return pos[STAGE_INDEX_Y_TILT]

    def resetToSafeState(self) -> None:
        """Set the microscope into its safe state.

        The safe state will set the microscope not to be in lorenz mode anymore.
        In addition the stage is driven to its origin, with resolving the tilt 
        in all axes.
        """
        # lock the microscope
        self._action_lock.acquire()

        # switch off the beam
        # self._feg.SetBeamValve(0)
        # self._feg.SetFEGEmissionOff(1)
        # self._gun.SetBeamSw(0)
        # self._aperture.SetBeamBlank(1)

        # reset the lorenz mode
        self.setInLorenzMode(False)

        # set the stage to the original position
        self._stage.SetOrg()
        self._action_lock.release()
    
    @staticmethod
    def defineConfigurationOptions(configuration: "AbstractConfiguration"):
        """Define which configuration options this class requires.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration to define the required options in
        """
        
        # add the option for the calibration factor
        configuration.addConfigurationOption(
            CONFIG_PYJEM_MICROSCOPE_GROUP, 
            "objective-lense-magnetic-field-calibration", 
            datatype=float, 
            description=("The calibration factor for the objective lense to " + 
            "set the magnetic field at the probe position. The calibration " + 
            "factor is defined as the magnetic field per current. The unit is " + 
            "then [magnetic field]/[current]."), 
            restart_required=True
        )

        configuration.addConfigurationOption(
            CONFIG_PYJEM_MICROSCOPE_GROUP, 
            "magnetic-field-unit", 
            datatype=str, 
            description=("The unit the magnetic field is measured in if the " + 
                "calibration factor is given."), 
            restart_required=True
        )
        
def format_hex(v: typing.Any, f: typing.Optional[str]="") -> str:
    """Format the given value for the given format.

    Parameters
    ----------
    v : any
        The value to format
    f : str
        The format specification
    
    Returns
    -------
    str
        The formatted value
    """

    f = list(Datatype.split_format_spec(f))
    # alternative form, this will make 0x<number>
    f[3] = "#"
    # convert to hex
    f[8] = "x"
    # remove precision, raises error otherwise
    f[7] = ""

    return Datatype.join_format_spec(f).format(hex_int.parse(v))

def parse_hex(v):
    """Parse the given value.

    Parameters
    ----------
    v : int, float, str, any
        If int or float are given, the number is returned as an int, if a
        string is given it is treated as a hex number (values after the decimal
        separator are ignored), everything else will be tried to convert to a 
        16 base int
    
    Returns
    -------
    int
        The converted int
    """

    if isinstance(v, (int, float)):
        return int(v)
    elif isinstance(v, str):
        v = v.split(".")
        return int(v[0], base=16)
    else:
        return int(v, base=16)

hex_int = Datatype(
    "hex", 
    format_hex,
    parse_hex
)