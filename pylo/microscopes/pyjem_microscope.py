import math
import time
import typing

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

# for development only
try:
    import dev_constants
    load_from_dev = True
except (ModuleNotFoundError, ImportError) as e:
    load_from_dev = False

if load_from_dev:
    import sys
    if hasattr(dev_constants, "pyjem_path"):
        if not dev_constants.pyjem_path in sys.path:
            sys.path.insert(0, dev_constants.pyjem_path)

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

        # the factor to multiply the focus with to show it to the user, 
        # the user entered values will be divided by this factor and then 
        # passed to the PyJEM functions
        try:
            focus_calibration_factor = (
                self.controller.configuration.getValue(
                    CONFIG_PYJEM_MICROSCOPE_GROUP, 
                    "focus-calibration"
                )
            )
        except KeyError:
            focus_calibration_factor = None

        if (not isinstance(focus_calibration_factor, (int, float)) or 
            math.isclose(focus_calibration_factor, 0)):
            focus_calibration_factor = None
        
        # the factor to get from the objective fine lense value to the 
        # objective coarse lense value
        try:
            self.objective_lense_coarse_fine_stepwidth = (
                self.controller.configuration.getValue(
                    CONFIG_PYJEM_MICROSCOPE_GROUP, 
                    "objective-lense-coarse-fine-stepwidth"
                )
            )
        except KeyError:
            self.objective_lense_coarse_fine_stepwidth = None
        
        if (not isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)) or 
            math.isclose(self.objective_lense_coarse_fine_stepwidth, 0)):
            self.objective_lense_coarse_fine_stepwidth = None

        # the factor to multiply the lense current with to get the magnetic
        # field
        try:
            magnetic_field_calibration_factor = (
                self.controller.configuration.getValue(
                    CONFIG_PYJEM_MICROSCOPE_GROUP, 
                    "objective-lense-magnetic-field-calibration"
                )
            )
        except KeyError:
            magnetic_field_calibration_factor = None
        
        if (not isinstance(magnetic_field_calibration_factor, (int, float)) or 
            math.isclose(magnetic_field_calibration_factor, 0)):
            magnetic_field_calibration_factor = None
        
        if magnetic_field_calibration_factor is not None:
            # the units of the magnetic field that results when multiplying with 
            # the magnetic_field_calibration_factor
            try:
                magnetic_field_unit = (
                    self.controller.configuration.getValue(
                        CONFIG_PYJEM_MICROSCOPE_GROUP, 
                        "magnetic-field-unit"
                    )
                )
            except KeyError:
                magnetic_field_unit = None
        else:
            magnetic_field_unit = None

        if isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)):
            max_ol_current = (0xFFFF * self.objective_lense_coarse_fine_stepwidth + 
                              0xFFFF)
        else:
            max_ol_current = 0xFFFF

        # limits taken from 
        # PyJEM/doc/interface/TEM3.html#PyJEM.TEM3.EOS3.SetObjFocus
        self.registerMeasurementVariable(
            MeasurementVariable(
                "focus", 
                "Focus (absolut)", 
                min_value=-1, 
                max_value=1000, 
                # unit="µm", # micrometer
                unit="um", # micrometer
                format=Datatype.int,
                # step by one increases the focus (in LOWMag-Mode) by 3 microns
                calibration=focus_calibration_factor
            ),
            self._getFocus,
            self._setFocus
        )
        
        # tilt limits depend on holder
        self.registerMeasurementVariable(
            MeasurementVariable("x-tilt", "X Tilt", -10, 10, "deg"),
            self._getXTilt,
            self._setXTilt
        )
        
        self.registerMeasurementVariable(
            MeasurementVariable("y-tilt", "Y Tilt", 0, 0, "deg"),
            self._getYTilt,
            self._setYTilt
        )

        self.registerMeasurementVariable(
            MeasurementVariable(
                "ol-current", 
                "Objective Lense Current", 
                unit="hex",
                format=Datatype.hex_int,
                min_value=0x0,
                max_value=max_ol_current,
                calibrated_unit=magnetic_field_unit,
                calibrated_name="Magnetic Field",
                calibration=magnetic_field_calibration_factor,
                calibrated_format=float
            ),
            self._getObjectiveLenseCurrent,
            self._setObjectiveLenseCurrent
        )

        # lenses
        self._lense_control = Lens3()
        # stage
        self._stage = Stage3()
        # electron opcical system
        self._eos = EOS3()
        # field emission gun
        self._feg = FEG3()
        # gun
        self._gun = GUN3()
        # aperture
        self._aperture = Apt3()

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
        - olf: The OLf value (objective fine lense current)
        - olc: The OLc value (objective coarse lense current)
        - om1: The OM value (objective mini lense current)
        - om2: The OM2 value (second objective mini lense current)
        - probe-mode: The probe mode as a `PROBE_MODE_*` constant
        - function-mode: The probe mode as a `FUNCTION_MODE_*` constant

        Returns
        -------
        dict
            The state dict
        """

        get = lambda v, i: v[i] if isinstance(v, (list, tuple)) else v

        state = {
            "cl1": get(self._lense_control.GetCL1(), 1),
            "cl2": get(self._lense_control.GetCL2(), 1),
            "cl3": get(self._lense_control.GetCL3(), 1),
            "il1": get(self._lense_control.GetIL1(), 1),
            "il2": get(self._lense_control.GetIL2(), 1),
            "il3": get(self._lense_control.GetIL3(), 1),
            "il4": get(self._lense_control.GetIL4(), 1),
            "pl1": get(self._lense_control.GetPL1(), 1),
            "pl2": get(self._lense_control.GetPL2(), 1),
            "pl3": get(self._lense_control.GetPL3(), 1),
            "olc": get(self._lense_control.GetOLc(), 1),
            "olf": get(self._lense_control.GetOLf(), 1),
            "om1": get(self._lense_control.GetOM(), 1),
            "om2": get(self._lense_control.GetOM2(), 1),
            # cannot set this value, there is no setter
            # "om2f": get(self._lense_control.GetOM2Flag(), 1),
            "probe-mode": get(self._eos.GetProbeMode(), 0),
            "function-mode": get(self._eos.GetFunctionMode(), 0),
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

        This function blocks the `MicroscopeInterface::action_lock`.

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

        self.action_lock.acquire()

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
            elif key == "olf": 
                self._lense_control.SetOLf(value)
            elif key == "olc": 
                self._lense_control.SetOLc(value)
            elif key == "om1": 
                # self._lense_control.SetOM(value)
                self._lense_control.SetFLCAbs(OM1_LENSE_ID, value)
            elif key == "om2": 
                self._lense_control.SetFLCAbs(OM2_LENSE_ID, value)
            elif key == "probe-mode":
                self._eos.SelectProbMode(value)
            elif key == "function-mode":
                self._eos.SelectFunctionMode(value)
            elif not ignore_invalid_keys:
                self.action_lock.release()
                raise KeyError("The key '{}' is invalid.".format(key))
        
        self.action_lock.release()
    
    def setInLorentzMode(self, lorentz_mode : bool) -> None:
        """Set the microscope to be in lorentz mode.

        This sets the probe mode to *TEM* and the function mode to *LowMAG*. It
        disables the objective lense (OL fine and coarse) and sets them to 0.

        Raises
        ------
        IOError
            When there is no holder inserted.

        Parameters
        ----------
        lorentz_mode : bool
            Whether the microscope should be in lorentz mode or not
        """

        # if self._stage.GetHolderStts() == 0:
        #     raise IOError("The holder is not inserted.")

        if lorentz_mode:
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
    
    def getInLorentzMode(self) -> bool:
        """Get whether the microscope is in the lorentz mode.

        This will return true if the objective fine and coarse lenses are 
        switched to free lense control and their current is 0.
        """

        # get the probe mode, the documentation sais it returns the probe  mode
        # id as an int but the (offline) code actually returns a tuple, don't 
        # know about the real microscope communication return value yet
        probe_mode = self._eos.GetProbeMode()
        if isinstance(probe_mode, (list, tuple)):
            probe_mode = probe_mode[0]

        function_mode = self._eos.GetFunctionMode()
        if isinstance(function_mode, (list, tuple)):
            function_mode = function_mode[0]
        
        lorentz_mode = (
            probe_mode == PROBE_MODE_TEM and 
            function_mode == FUNCTION_MODE_TEM_LowMAG
        )

        return lorentz_mode
    
    def _setFocus(self, value : int) -> None:
        """Set the focus to the given value.

        Typical values are between -1 and 50.

        Parameters
        ----------
        value : int
            The focus value
        """
        
        diff = value - self._focus
        self._eos.SetObjFocus(int(diff))
        # self._eos.SetDiffFocus(value) +-1 to 50
        # self._lense_control.SetDiffFocus(value) +-1 to 50
        # self._lense_control.SetILFocus(value)
        # self._lense_control.SetPLFocus(value)
        self._focus = value

    def _setObjectiveLenseCurrent(self, value : float) -> None:
        """Set the objective lense current.

        The value corresponds to I/O output value without carry.
        
        Parameters
        ----------
        value : int or float
            The value to set the objective lense current to in objective fine
            lense steps
        """

        if not self.isValidMeasurementVariableValue("ol-current", value):
            raise ValueError(("The value {} is not allowed for the " + 
                              "objective lense current.").format(value))

        if isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)):
            self._lense_control.SetOLc(value // self.objective_lense_coarse_fine_stepwidth)
            self._lense_control.SetOLf(value % self.objective_lense_coarse_fine_stepwidth)
        else:
            self._lense_control.SetOLf(value)
    
    def _setXTilt(self, value : float) -> None:
        """Set the x tilt in degrees.

        It will execute until the x tilt is set correctly.
        
        Parameters
        ----------
        value : int or float
            The value to set the x tilt in degrees.
        """

        if not self.isValidMeasurementVariableValue("x-tilt", value):
            raise ValueError(("The value {} is not allowed for the " + 
                              "x tilt.").format(value))

        # tell it to move to the given x angle
        self._stage.SetTiltXAngle(value)

        # wait until the x tilt has the desired value
        while self._stage.GetStatus()[STAGE_INDEX_X_TILT] == STAGE_STATUS_MOVING:
            time.sleep(0.1)

    def _setYTilt(self, value : float) -> None:
        """Set the y tilt in degrees.

        It will execute until the y tilt is set correctly.

        Note that not all probe holders support a y tilt!
        
        Parameters
        ----------
        value : int or float
            The value to set the y tilt in degrees.
        """

        if not self.isValidMeasurementVariableValue("y-tilt", value):
            raise ValueError(("The value {} is not allowed for the " + 
                              "y tilt.").format(value))

        # tell it to move to the given y angle
        self._stage.SetTiltYAngle(value)

        # wait until the y tilt has the desired value
        while self._stage.GetStatus()[STAGE_INDEX_Y_TILT] == STAGE_STATUS_MOVING:
            time.sleep(0.1)
    
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

        # GetObjFocus() doesn't exist, no idea how to get the focus value 
        # (except for saving it but that is only the last escape, this makes it
        # impossible to check if the focus really is set correctly)
        # self._eos.GetObjFocus()

        return self._focus
    
    def _getObjectiveLenseCurrent(self) -> float:
        """Get the objective lense current in the current units.

        Returns
        -------
        float
            The actual current of the objective lense at the microscope,
            measured in objective fine lense steps
        """

        fine_value = self._lense_control.GetOLf()
        if isinstance(fine_value, (list, tuple)):
            fine_value = fine_value[1]

        coarse_value = self._lense_control.GetOLc()
        if isinstance(coarse_value, (list, tuple)):
            coarse_value = coarse_value[1]

        if isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)):
            value = (coarse_value * self.objective_lense_coarse_fine_stepwidth + 
                     fine_value)
        else:
            value = fine_value

        return value
    
    def _getXTilt(self) -> float:
        """Get the x tilt in degrees.

        Returns
        -------
        float
            The x tilt
        """

        # wait until the x tilt is not changing anymore
        while self._stage.GetStatus()[STAGE_INDEX_X_TILT] == STAGE_STATUS_MOVING:
            time.sleep(0.1)

        # get the current stage position (includes the tilt)
        pos = self._stage.GetPos()

        return round(pos[STAGE_INDEX_X_TILT], 2)
    
    def _getYTilt(self) -> float:
        """Get the y tilt in degrees.

        Returns
        -------
        float
            The y tilt
        """

        # wait until the y tilt is not changing anymore
        while self._stage.GetStatus()[STAGE_INDEX_Y_TILT] == STAGE_STATUS_MOVING:
            time.sleep(0.1)

        # get the current stage position (includes the tilt)
        pos = self._stage.GetPos()

        return round(pos[STAGE_INDEX_Y_TILT], 2)

    def resetToSafeState(self) -> None:
        """Set the microscope into its safe state.

        The safe state will set the microscope not to be in lorentz mode anymore.
        In addition the stage is driven to its origin, with resolving the tilt 
        in all axes.

        This function blocks the `MicroscopeInterface.action_lock` while 
        operating.
        """

        # reset the lorentz mode
        self.setInLorentzMode(False)

        # lock the microscope after the lorentz mode, otherwise there is a 
        # deadlock (this function blocks the lock, 
        # PyJEMMicroscope::setInLorentzMode() waits for the lock)
        self.action_lock.acquire()

        # close the beam valve
        # documentation sais: "This works for FEG and 3100EF" for 
        # FEG3::SetBeamValve() and for FEG3::setFEGEmissionOff()
        self._feg.SetBeamValve(0)

        # Do not change emission, if there are bad values and it is 
        # switched on, this may have bad effects
        # self._feg.SetFEGEmissionOff(1)

        # the documentation sais: "This does not work for FEG"
        # same for the gun, do not touch the gun, this may have bad
        # side effects
        # self._gun.SetBeamSw(0)

        # beam blanking, should not be used but may be used for emergency mode
        # self._aperture.SetBeamBlank(1)

        # set the stage to the original position
        self._stage.SetOrg()

        # release the lock, the setCurrentState() needs the lock again
        self.action_lock.release()

        # restore the starting state
        self.setCurrentState(self._init_state)
    
    @staticmethod
    def defineConfigurationOptions(configuration: "AbstractConfiguration"):
        """Define which configuration options this class requires.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration to define the required options in
        """
        
        # add the stepwidth of the objective coarse lense in objective fine 
        # lense units
        configuration.addConfigurationOption(
            CONFIG_PYJEM_MICROSCOPE_GROUP, 
            "objective-lense-coarse-fine-stepwidth", 
            datatype=float, 
            description=("The factor to calculate between the fine and " + 
            "coarse objective lense. One step with the objective coarse " + 
            "value is equal to this value steps with the objective fine " + 
            "lense. So OL-fine * value = OL-coarse."), 
            restart_required=True,
            default_value=32
        )
        
        # add the option for the calibration factor for the focus
        configuration.addConfigurationOption(
            CONFIG_PYJEM_MICROSCOPE_GROUP, 
            "focus-calibration", 
            datatype=float, 
            description=("The calibration factor for the focus. The " + 
            "focus set in the GUI will be divided by this factor to pass " + 
            "it to the PyJEM functions. The focus received by the PyJEM " + 
            "functions will be multiplied with this factor and then shown."), 
            restart_required=True,
            default_value=3
        )
        
        # add the option for the calibration factor for the magnetic field
        configuration.addConfigurationOption(
            CONFIG_PYJEM_MICROSCOPE_GROUP, 
            "objective-lense-magnetic-field-calibration", 
            datatype=float, 
            description=("The calibration factor for the objective lense to " + 
            "set the magnetic field at the probe position. The calibration " + 
            "factor is defined as the magnetic field per current. The unit is " + 
            "then [magnetic field]/[current]."), 
            restart_required=True,
            default_value=0
        )

        # add the option for the magnetic field unit to display
        configuration.addConfigurationOption(
            CONFIG_PYJEM_MICROSCOPE_GROUP, 
            "magnetic-field-unit", 
            datatype=str, 
            description=("The unit the magnetic field is measured in if the " + 
                "calibration factor is given."), 
            restart_required=True
        )