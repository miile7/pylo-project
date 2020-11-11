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

try:
    import DigitalMicrograph as DM
except (ModuleNotFoundError, ImportError) as e:
    DM = None

# for development only
try:
    import dev_constants
    load_from_dev = True
except (ModuleNotFoundError, ImportError) as e:
    load_from_dev = False

if load_from_dev:
    import sys
    if hasattr(dev_constants, "execdmscript_path"):
        if not dev_constants.execdmscript_path in sys.path:
            sys.path.insert(0, dev_constants.execdmscript_path)

import execdmscript

from ..events import microscope_ready
from ..datatype import Datatype
from ..stop_program import StopProgram
from .microscope_interface import MicroscopeInterface
from ..measurement_variable import MeasurementVariable

# the group name in the configuration for settings that are related to this
# microscope
CONFIG_PYJEM_MICROSCOPE_GROUP = "dm-microscope"

# illumination modes = PyJEM Probe Mmodes
ILLUMINATION_MODE_TEM = "TEM"
ILLUMINATION_MODE_CsTEM = "CsTEM"
ILLUMINATION_MODE_EDS = "EDS"
ILLUMINATION_MODE_NBD = "NBD"
ILLUMINATION_MODE_CBD = "CBD"
ILLUMINATION_MODE_PROBE = "PROBE"
ILLUMINATION_MODE_STEM = "STEM"

# imaging optics modes (= function modes in PyJEM) for TEM
IMAGING_OPTICS_MODE_MAG = "MAG"
IMAGING_OPTICS_MODE_MAG2 = "MAG2"
IMAGING_OPTICS_MODE_LowMAG = "LowMAG"
IMAGING_OPTICS_MODE_SAMAG = "SAMAG"
IMAGING_OPTICS_MODE_DIFF = "DIFF"

# imaging optics modes (= function modes in PyJEM) for STEM mode
IMAGING_OPTICS_MODE_ALIGN = "ALIGN"
IMAGING_OPTICS_MODE_UUDIFF = "UUDIFF"
IMAGING_OPTICS_MODE_ROCKING = "ROCKING"

# imaging modes (= function modes in PyJEM) for ??
IMAGING_OPTICS_MODE_LMAG = "LMAG"
IMAGING_OPTICS_MODE_AMAG = "AMAG"
IMAGING_OPTICS_MODE_RESERVE = "RESERVE"
IMAGING_OPTICS_MODE_MAG1 = "MAG1"

# gif detector imaging modes
# https://eels.info/products/tem-gif-integration
IMAGING_OPTICS_MODE_GIF_MAG1 = "GIF MAG1"
IMAGING_OPTICS_MODE_GIF_MAG2 = "GIF MAG2"
IMAGING_OPTICS_MODE_GIF_LowMAG = "GIF LowMAG"
IMAGING_OPTICS_MODE_GIF_SAMAG = "GIF SAMAG"
IMAGING_OPTICS_MODE_GIF_DIFF = "GIF DIFF"

class DMMicroscope(MicroscopeInterface):
    """This class is the interface for communicating with the interface 
    integrated in Gatan Microscope Suite (GMS/Digital Micrograph/DM).
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
        
        # # the factor to get from the objective fine lense value to the 
        # # objective coarse lense value
        # try:
        #     self.objective_lense_coarse_fine_stepwidth = (
        #         self.controller.configuration.getValue(
        #             CONFIG_PYJEM_MICROSCOPE_GROUP, 
        #             "objective-lense-coarse-fine-stepwidth"
        #         )
        #     )
        # except KeyError:
        #     self.objective_lense_coarse_fine_stepwidth = None
        
        # if (not isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)) or 
        #     math.isclose(self.objective_lense_coarse_fine_stepwidth, 0)):
        #     self.objective_lense_coarse_fine_stepwidth = None

        # # the factor to multiply the lense current with to get the magnetic
        # # field
        # try:
        #     magnetic_field_calibration_factor = (
        #         self.controller.configuration.getValue(
        #             CONFIG_PYJEM_MICROSCOPE_GROUP, 
        #             "objective-lense-magnetic-field-calibration"
        #         )
        #     )
        # except KeyError:
        #     magnetic_field_calibration_factor = None
        
        # if (not isinstance(magnetic_field_calibration_factor, (int, float)) or 
        #     math.isclose(magnetic_field_calibration_factor, 0)):
        #     magnetic_field_calibration_factor = None
        
        # if magnetic_field_calibration_factor is not None:
        #     # the units of the magnetic field that results when multiplying with 
        #     # the magnetic_field_calibration_factor
        #     try:
        #         magnetic_field_unit = (
        #             self.controller.configuration.getValue(
        #                 CONFIG_PYJEM_MICROSCOPE_GROUP, 
        #                 "magnetic-field-unit"
        #             )
        #         )
        #     except KeyError:
        #         magnetic_field_unit = None
        # else:
        #     magnetic_field_unit = None

        # if isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)):
        #     max_ol_current = (0xFFFF * self.objective_lense_coarse_fine_stepwidth + 
        #                       0xFFFF)
        # else:
        #     max_ol_current = 0xFFFF
        
        # self.registerMeasurementVariable(
        #     MeasurementVariable(
        #         "ol-current", 
        #         "Objective Lense Current", 
        #         unit="hex",
        #         format=Datatype.hex_int,
        #         min_value=0x0,
        #         max_value=max_ol_current,
        #         calibrated_unit=magnetic_field_unit,
        #         calibrated_name="Magnetic Field",
        #         calibration=magnetic_field_calibration_factor,
        #         calibrated_format=float
        #     ),
        #     self._getObjectiveLensCurrent,
        #     self._setObjectiveLensCurrent
        # )
        
        # tilt limits depend on holder
        self.registerMeasurementVariable(
            MeasurementVariable("x-tilt", "X Tilt", -10, 10, "deg"),
            self._getXTilt,
            self._setXTilt
        )

        self.holders = ("Default holder", "Tilt holder") 
        self.installed_probe_holder, *_ = self.controller.view.askFor({
            "name": "Installed probe holder",
            "datatype": Datatype.options(self.holders),
            "description": ("Please select the holder that is currently " + 
                            "installed and used for the measurement. If you " +
                            "want to use a different holder, change it now. " + 
                            "\n\n" + 
                            "Note that entering a wrong holder will " + 
                            "initialize the microscope wrong which may " + 
                            "cause damage.")
        })

        self.holder_confirmed = True
        if self.installed_probe_holder == "Tilt holder":
            self.registerMeasurementVariable(
                MeasurementVariable("y-tilt", "Y Tilt", -15, 15, "deg"),
                self._getYTilt,
                self._setYTilt
            )
            # extra ask for the user if the tilt holder really is installed, 
            # just to be extra sure
            self.holder_confirmed = False
        microscope_ready.append(self._confirmHolder)

        # save current focus, there is no get function
        self._focus = 0

        from ..config import OFFLINE_MODE

        if DM is not None and not OFFLINE_MODE:
            self.dm_microscope = DM.Py_Microscope()
        else:
            self.dm_microscope = None
    
    def _confirmHolder(self) -> None:
        """Show a confirm dialog with the view if the holder is not yet
        confirmed.

        Raises
        ------
        StopProgram
            If the user clicks 'cancel'
        """

        if not self.holder_confirmed:
            button = self.controller.view.askForDecision(
                ("Please confirm, that the probe holder '{}' really is " + 
                 "installed at the microscope.").format(self.installed_probe_holder),
                ("Yes, it is installed", "Cancel"))
            
            if button == 0:
                self.holder_confirmed = True
            else:
                raise StopProgram()
    
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

        # from .config import DEFAULT_DM_SET_OPTICS_MODE
        DEFAULT_DM_SET_OPTICS_MODE = True

        if DEFAULT_DM_SET_OPTICS_MODE:
            script = "EMSetImagingOpticsMode(\"{}\");".format(
                IMAGING_OPTICS_MODE_LowMAG)
            with execdmscript.exec_dmscript(script):
                pass
        else:
            raise NotImplementedError("Manual setting of the lorentz mode " + 
                                      "is not yet implemented.")
    
    def getInLorentzMode(self) -> bool:
        """Get whether the microscope is in the lorentz mode.

        This will return true if the objective fine and coarse lenses are 
        switched to free lense control and their current is 0.
        """
        
        if self.dm_microscope.CanGetImagingOpticsMode():
            return (self.dm_microscope.GetImagingOpticsMode() == 
                    IMAGING_OPTICS_MODE_LowMAG)
        else:
            raise IOError("Cannot get the optics mode.")

    def _setObjectiveLensCurrent(self, value: float) -> None:
        """Set the objective lense current.

        The value corresponds to I/O output value without carry.
        
        Parameters
        ----------
        value : int or float
            The value to set the objective lense current to in objective fine
            lense steps
        """
        raise NotImplementedError("The objective lens current is not yet implemented!")
    
    def _getObjectiveLensCurrent(self) -> float:
        """Get the objective lense current in the current units.

        Returns
        -------
        float
            The actual current of the objective lense at the microscope,
            measured in objective fine lense steps
        """
        raise NotImplementedError("The objective lens current is not yet implemented!")
    
    def _getObjectiveLenseCurrent(self) -> float:
        """Get the objective lense current in the current units.

        Returns
        -------
        float
            The actual current of the objective lense at the microscope,
            measured in objective fine lense steps
        """
        raise NotImplementedError("The objective lens current is not yet implemented!")
    
    def _getObjectiveLenseCurrent(self) -> float:
        """Get the objective lense current in the current units.

        Returns
        -------
        float
            The actual current of the objective lense at the microscope,
            measured in objective fine lense steps
        """
        pass
    
    def _setXTilt(self, value: float) -> None:
        """Set the x tilt in degrees.

        It will execute until the x tilt is set correctly.
        
        Parameters
        ----------
        value : int or float
            The value to set the x tilt in degrees.
        """
        # self.dm_microscope.SetStageBeta(value)
        self.dm_microscope.SetStageAlpha(value)
    
    def _getXTilt(self) -> float:
        """Get the x tilt in degrees.

        Returns
        -------
        float
            The x tilt
        """
        # return self.dm_microscope.GetStageBeta()
        return self.dm_microscope.GetStageAlpha()

    def _setYTilt(self, value: float) -> None:
        """Set the y tilt in degrees.

        It will execute until the y tilt is set correctly.

        Note that not all probe holders support a y tilt!
        
        Parameters
        ----------
        value : int or float
            The value to set the y tilt in degrees.
        """
        self._confirmHolder()
        self.dm_microscope.SetStageBeta(value)
        # self.dm_microscope.SetStageAlpha(value)
    
    def _getYTilt(self) -> float:
        """Get the y tilt in degrees.

        ReturnsY
        -------
        float
            The y tilt
        """
        return self.dm_microscope.GetStageBeta()
        # return self.dm_microscope.GetStageAlpha()
    
    def _setFocus(self, value: float) -> None:
        """Set the focus to the given value.

        Typical values are between -1 and 50.

        Parameters
        ----------
        value : int
            The focus value
        """
        self.dm_microscope.SetFocus(value)
        # self.dm_microscope.SetCalibratedFocus(value)
    
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
        return self.dm_microscope.GetFocus()
        # return self.dm_microscope.GetCalibratedFocus()

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

        if self.dm_microscope.HasBeamBlanker():
            self.dm_microscope.SetBeamBlanked(True)

        # release the lock, the setCurrentState() needs the lock again
        self.action_lock.release()
    
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
        # configuration.addConfigurationOption(
        #     CONFIG_PYJEM_MICROSCOPE_GROUP, 
        #     "objective-lense-coarse-fine-stepwidth", 
        #     datatype=float, 
        #     description=("The factor to calculate between the fine and " + 
        #     "coarse objective lense. One step with the objective coarse " + 
        #     "value is equal to this value steps with the objective fine " + 
        #     "lense. So OL-fine * value = OL-coarse."), 
        #     restart_required=True,
        #     default_value=32
        # )
        
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
            restart_required=True
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