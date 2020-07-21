import threading
import time

try:
    import PyJEM.TEM3 as TEM3
except:
    import PyJEM.offline.TEM3 as TEM3

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
    """This class is the interface for communicating with the JEOL NeoARM F200
    TEM.

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
    
    lens3.SetNtrl((Lens3)arg1, (int)arg2)
        NTRL within only value range.
        0:Brightness, 1:OBJ Focus, 2:DIFF Focus, 3:IL Focus, 4:PL Focus, 5:FL Focus


    Attributes
    ----------
    magnetic_field_calibration_factor : float
        The calibration factor to calculate the magentic field from the current 
        by multiplying the current with the `magnetic_field_calibration_factor`, 
        so this is the magnetic field per current
    """
    
    def __init__(self, controller : "Controller"):
        """Get the microscope instance"""
        super().__init__(controller)

        # set all measurement variables sequential, not parallel
        self.supports_parallel_measurement_variable_setting = False

        self.supported_measurement_variables = [
            # limits taken from 
            # PyJEM/doc/interface/TEM3.html#PyJEM.TEM3.EOS3.SetObjFocus
            MeasurementVariable("focus", "Focus", -1, 50),
            MeasurementVariable("x-tilt", "X Tilt", -10, 10, "deg"),
            MeasurementVariable("y-tilt", "Y Tilt", -10, 10, "deg"),
        ]

        try:
            self.magnetic_field_calibration_factor = (
                self.controller.configuration.getValue(
                    CONFIG_PYJEM_MICROSCOPE_GROUP, 
                    "objective-lense-magnetic-field-calibration"))
        except KeyError:
            self.magnetic_field_calibration_factor = None

        if isinstance(self.magnetic_field_calibration_factor, (int, float)):
            self.supported_measurement_variables.append(
                MeasurementVariable("magnetic-field", "Magnetic field", 
                    self._getMagneticFieldForObjectiveLenseCurrent(0), 
                    self._getMagneticFieldForObjectiveLenseCurrent(1)
                )
            )
        else:
            self.supported_measurement_variables.append(
                MeasurementVariable("ol-current", "Objective lense current", 0, 1)
            )

        self._lense_control = TEM3.lens3.Lens3()
        self._stage = TEM3.stage3.Stage3()
        # Electron opcical system
        self._eos = TEM3.eos3.EOS3()
        self._action_lock = threading.Lock()
    
    def _getMagneticFieldForObjectiveLenseCurrent(self, current: float) -> float:
        """Get the magnetic field for the given objective lense current.

        This only works if the 
        `PyJEMMicroscope::magnetic_field_calibration_factor` is given which is 
        not always the case. In this case an `AttributeError` is raised.

        Raises
        ------
        AttributeError
            When the `PyJEMMicroscope::magnetic_field_calibration_factor` is not
            given
        
        Parameters
        ----------
        current : float
            The current value in the current specific units

        Returns
        -------
        float
            The magnetic field
        """
        
        if not isinstance(self.magnetic_field_calibration_factor, (int, float)):
            raise AttributeError("The magnetic field is not calibrated. This " + 
                                 "can be done by either setting the " + 
                                 "'magnetic_field_calibration_factor' " + 
                                 "attribute or by setting the facotor in the " + 
                                 "configuration.")
        
        return current * self.magnetic_field_calibration_factor
    
    def _getObjectiveLenseCurrentForMagneticField(self, magnetic_field: float) -> float:
        """Get the objective lense current for the given magnetic field.

        This only works if the 
        `PyJEMMicroscope::magnetic_field_calibration_factor` is given which is 
        not always the case. In this case an `AttributeError` is raised.

        Raises
        ------
        AttributeError
            When the `PyJEMMicroscope::magnetic_field_calibration_factor` is not
            given
        
        Parameters
        ----------
        magnetic_field : float
            The magnetic field in the field specific units

        Returns
        -------
        float
            The current value
        """
        
        if not isinstance(self.magnetic_field_calibration_factor, (int, float)):
            raise AttributeError("The magnetic field is not calibrated. This " + 
                                 "can be done by either setting the " + 
                                 "'magnetic_field_calibration_factor' " + 
                                 "attribute or by setting the facotor in the " + 
                                 "configuration.")
        
        return magnetic_field / self.magnetic_field_calibration_factor
    
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
        
        lorenz_mode = (self._lense_control.GetFLCInfo(OL_FINE_LENSE_ID) == 1 and
                       self._lense_control.GetFLCInfo(OL_COARSE_LENSE_ID) == 1 and 
                       self._lense_control.GetOLc() == 0 and 
                       self._lense_control.GetOLf() == 0)
        
        # let other functions access the microscope
        self._action_lock.release()

        return lorenz_mode
    
    def setMeasurementVariableValue(self, id_: str, value: float) -> None:
        """Set the measurement variable defined by its id to the given value.

        The JEOL NeoARM F200 supports the following variables:
        - 'focus': The focus current in ?
        - 'ol-current' or 'magnetic-field': The objective lense current which 
          induces a magnetic field, if the calibration factor is given only the 
          'magnetic-field' can be used, if not only the 'ol-current' can be 
          used
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
        elif id_ == "ol-current":
            self._setObjectiveLenseCurrent(value)
        elif id_ == "magnetic-field":
            self._setObjectiveLenseCurrent(
                self._getObjectiveLenseCurrentForMagneticField(value)
            )
        elif id_ == "x-tilt":
            self._setXTilt(value)
        elif id_ == "y-tilt": 
            self._setYTilt(value)
        else:
            # this cannot happen, if the id doesn't exist the 
            # MicroscopeInterface::isValidMeasurementVariableValue returns 
            # false
            raise ValueError("The id {} does not exist.".format(id_))
    
    def _setFocus(self, value : float):
        """Set the focus to the given value.

        Typical values are between -1 and 50.

        Parameters
        ----------
        value : float
            The focus value
        """

        raise Exception("The focus does not properly work at the moment. This " + 
                        "probably is the wrong focus.")

        self._action_lock.acquire()
        self._eos.SetObjFocus(value)
        # self._eos.SetDiffFocus(value) +-1 to 50
        # self._lense_control.SetDiffFocus(value) +-1 to 50
        # self._lense_control.SetILFocus(value)
        # self._lense_control.SetPLFocus(value)
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

        if not self.isValidMeasurementVariableValue("ol-current", value):
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

        Raises
        ------
        ValueError
            When there is no `MeasurementVariable` for the `id_`.
        """

        if id_ == "focus":
            return self._getFocus()
        elif id_ == "ol-current":
            return self._getObjectiveLenseCurrent()
        elif id_ == "magnetic-field":
            return self._getMagneticFieldForObjectiveLenseCurrent(
                self._getObjectiveLenseCurrent()
            )
        elif id_ == "x-tilt":
            self._getXTilt()
        elif id_ == "y-tilt":
            self._getYTilt()
        else:
            raise ValueError(("There is no MeasurementVariable for the " + 
                              "id {}.").format(id_))
    
    def _getFocus(self) -> float:
        self._action_lock.acquire()

        # GetObjFocus() doesn't exist, no idea how to get the focus value 
        # (except for saving it but that is only the last escape, this makes it
        # impossible to check if the focus really is set correctly)
        # self._eos.GetObjFocus()

        self._action_lock.release()
        raise Exception("Currently there is no possibility to get the focus.")
    
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