import math
import time
import typing
import logging

from pylo import FallbackModuleNotFoundError

try:
    import DigitalMicrograph as DM
except (FallbackModuleNotFoundError, ImportError) as e:
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

from pylo import microscope_ready

from pylo import pylolib
from pylo import Datatype
from pylo import logginglib
from pylo import StopProgram
from pylo import MicroscopeInterface
from pylo import MeasurementVariable

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
    
    def __init__(self, *args, **kwargs) -> None:
        """Get the microscope instance"""
        super().__init__(*args, **kwargs)

        self._logger = logginglib.get_logger(self)

        # set all measurement variables sequential, not parallel
        self.supports_parallel_measurement_variable_setting = False

        # the factor to multiply the focus with to show it to the user, 
        # the user entered values will be divided by this factor and then 
        # passed to the PyJEM functions
        try:
            focus_calibration_factor = pylolib.parse_value(float, 
                self.controller.configuration.getValue(
                    self.config_group_name, "focus-calibration"))
        except KeyError:
            focus_calibration_factor = None

        if (not isinstance(focus_calibration_factor, (int, float)) or 
            math.isclose(focus_calibration_factor, 0)):
            focus_calibration_factor = None
        
        if logginglib.do_log(self._logger, logging.DEBUG):
            self._logger.debug("Focus calibration is '{}'".format(
                               focus_calibration_factor))

        self.registerMeasurementVariable(
            MeasurementVariable(
                "om-current", 
                "Objective mini lens current", 
                min_value=0x0, 
                max_value=0xFFFF, 
                unit="hex",
                format=Datatype.hex_int,
                calibration=focus_calibration_factor,
                calibrated_name="Focus",
                calibrated_unit="um", # micrometer
                calibrated_format=Datatype.int
            ),
            self._getObjectiveMiniLensCurrent,
            self._setObjectiveMiniLensCurrent
        )
        
        if logginglib.do_log(self._logger, logging.DEBUG):
            self._logger.debug("Asking the user to set the focus to 0")
        
        # GMS needs some time here, don't know why but this fixes the bug, if 
        # the sleeping is removed, the dialog will never show up but the 
        # program will wait for interaction so it freezes
        time.sleep(0.1)
        button = self.controller.view.askForDecision(("Please set the focus " + 
            "to zero manually now. This will be  saved as the reference value."),
            ("Focus is 0 now", "Cancel"))
        
        if button == 1:
            err = StopProgram()
            if logginglib.do_log(self._logger, logging.DEBUG):
                self._logger.debug("Stopping program", exc_info=err)
            raise err
        
        # the factor to get from the objective fine lense value to the 
        # objective coarse lense value
        try:
            self.objective_lense_coarse_fine_stepwidth = pylolib.parse_value(
                Datatype.int, self.controller.configuration.getValue(
                    self.config_group_name, 
                    "objective-lense-coarse-fine-stepwidth"))
        except KeyError:
            self.objective_lense_coarse_fine_stepwidth = None
        
        if (not isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)) or 
            math.isclose(self.objective_lense_coarse_fine_stepwidth, 0)):
            self.objective_lense_coarse_fine_stepwidth = None
        
        if logginglib.do_log(self._logger, logging.DEBUG):
            self._logger.debug(("Objective fine-coarse lens stepwidth is " + 
                                "'{}'").format(
                                self.objective_lense_coarse_fine_stepwidth))

        # the factor to multiply the lense current with to get the magnetic
        # field
        try:
            magnetic_field_calibration_factor = pylolib.parse_value(float, 
                self.controller.configuration.getValue(
                    self.config_group_name, 
                    "objective-lense-magnetic-field-calibration"))
        except KeyError:
            magnetic_field_calibration_factor = None
        
        if (not isinstance(magnetic_field_calibration_factor, (int, float)) or 
            math.isclose(magnetic_field_calibration_factor, 0)):
            magnetic_field_calibration_factor = None
        
        if logginglib.do_log(self._logger, logging.DEBUG):
            self._logger.debug("Magnetic field calibration factor is '{}'".format(
                               magnetic_field_calibration_factor))
        
        if magnetic_field_calibration_factor is not None:
            # the units of the magnetic field that results when multiplying with 
            # the magnetic_field_calibration_factor
            try:
                magnetic_field_unit = (self.controller.configuration.getValue(
                        self.config_group_name, "magnetic-field-unit"))
            except KeyError:
                magnetic_field_unit = None
        else:
            magnetic_field_unit = None
        
        if logginglib.do_log(self._logger, logging.DEBUG):
            self._logger.debug("Magnetic field unit is '{}'".format(
                               magnetic_field_unit))

        if isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)):
            max_ol_current = (0xFFFF * self.objective_lense_coarse_fine_stepwidth + 
                              0xFFFF)
        else:
            max_ol_current = 0xFFFF
        
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
            self._getObjectiveLensCurrent,
            self._setObjectiveLensCurrent
        )
        self._ol_currents = {}
        
        # tilt limits depend on holder
        self.registerMeasurementVariable(
            MeasurementVariable("x-tilt", "X Tilt", -15, 15, "deg"),
            self._getXTilt,
            self._setXTilt
        )
        
        if logginglib.do_log(self._logger, logging.DEBUG):
            self._logger.debug("Asking the user for the holder")

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
        
        if logginglib.do_log(self._logger, logging.DEBUG):
            self._logger.debug("User selected '{}' holder".format(
                               self.installed_probe_holder))

        self.holder_confirmed = True
        if self.installed_probe_holder == "Tilt holder":
            self.registerMeasurementVariable(
                MeasurementVariable("y-tilt", "Y Tilt", -15, 15, "deg"),
                self._getYTilt,
                self._setYTilt
            )
            x_tilt = self.getMeasurementVariableById("x-tilt")
            x_tilt.min_value = -25
            x_tilt.max_value = 25
            # extra ask for the user if the tilt holder really is installed, 
            # just to be extra sure
            self.holder_confirmed = False
        microscope_ready.append(self._confirmHolder)

        from pylo.config import OFFLINE_MODE

        if DM is not None and not OFFLINE_MODE:
            if logginglib.do_log(self._logger, logging.DEBUG):
                self._logger.debug("Creating DigitalMicrograph.Py_Microscope")
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
            if logginglib.do_log(self._logger, logging.DEBUG):
                self._logger.debug("Asking user to confirm '{}' holder".format(
                                   self.installed_probe_holder))
            
            button = self.controller.view.askForDecision(
                ("Please confirm, that the probe holder '{}' really is " + 
                 "installed at the microscope.").format(self.installed_probe_holder),
                ("Yes, it is installed", "Cancel"))
            
            if button == 0:
                if logginglib.do_log(self._logger, logging.DEBUG):
                    self._logger.debug("'{}' holder is confirmed".format(
                                       self.installed_probe_holder))
                                    
                self.holder_confirmed = True
            else:
                err = StopProgram()
                if logginglib.do_log(self._logger, logging.DEBUG):
                    self._logger.debug("Holder rejected, stopping program", 
                                       exc_info=err)
                raise err
    
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

        if "use-em-optics-mode-set-function" in self.config_defaults:
            use_set_function = pylolib.parse_value(bool,
                self.config_defaults["use-em-optics-mode-set-function"])
        else:
            use_set_function = False
    
        if use_set_function:
            dmscript = "EMSetImagingOpticsMode(\"{}\");".format(
                IMAGING_OPTICS_MODE_LowMAG)
            
            if logginglib.do_log(self._logger, logging.DEBUG):
                self._logger.debug(("Setting microscope to lorentz mode by " + 
                                    "EMControl.dll (mode = '{}') with " + 
                                    "dmscript '{}'").format(
                                    IMAGING_OPTICS_MODE_GIF_LowMAG, dmscript))

            with execdmscript.exec_dmscript(dmscript):
                pass
        else:
            if logginglib.do_log(self._logger, logging.DEBUG):
                self._logger.debug("Asking the user to set the microscope " + 
                                   "into lorentz mode manually")
            
            self.controller.view.askForDecision("Please set the microscope " + 
                                                "into the lorentz mode.", 
                                                options=("In lorentz mode now", 
                                                         "Cancel"))

            if logginglib.do_log(self._logger, logging.DEBUG):
                self._logger.debug("User confirmed that the microscope is " + 
                                   "in lorentz mode now")
    
    def getInLorentzMode(self) -> bool:
        """Get whether the microscope is in the lorentz mode.

        This will return true if the objective fine and coarse lenses are 
        switched to free lense control and their current is 0.
        """

        # msg = ("DMMicroscope.getInLorentzMode(): DEBUG: ALWAYS RETURNING " + 
        #        "TRUE IN LORENTZ MODE")
        # print("+-{}-+".format("-" * len(msg)))
        # print("| {} |".format(msg))
        # print("+-{}-+".format("-" * len(msg)))
        # return True
        
        if self.dm_microscope.CanGetImagingOpticsMode():
            if logginglib.do_log(self._logger, logging.DEBUG):
                self._logger.debug("Checking if the microscope is in lorentz " + 
                                   "mode")
            
            lorentz = (self.dm_microscope.GetImagingOpticsMode() == 
                       IMAGING_OPTICS_MODE_LowMAG)

            if logginglib.do_log(self._logger, logging.DEBUG):
                self._logger.debug("Microscope returned '{}'".format(lorentz))
            
            return lorentz
        else:
            err = IOError("Cannot get the optics mode.")
            logginglib.log_error(self._logger, err)
            raise err

    def _setObjectiveLensCurrent(self, value: float) -> None:
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
        
        if ("value" in self._ol_currents and 
            math.isclose(self._ol_currents["value"], value)):
            # value is still the same from the last time
            if logginglib.do_log(self._logger, logging.DEBUG):
                self._logger.debug(("Setting objectiv lens current to '{}' " + 
                                    "but the current value is '{}', so the " + 
                                    "function is now skipped").format(value,
                                    self._ol_currents["value"]))
            
            return
        else:
            self._ol_currents["value"] = value

        # calculate the values if the coarse lens and the fine lens can be 
        # converted into eachother
        if isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)):
            self._ol_currents["coarse"] = value // self.objective_lense_coarse_fine_stepwidth
            self._ol_currents["fine"] = value % self.objective_lense_coarse_fine_stepwidth
        else:
            self._ol_currents["fine"] = value
        
        # tell the operator to set the values manually
        template = "{lens} value to '0x{value:x}' (decimal: '{value}')"
        text = "Please change the objectiv lens current manually. Set the "
        bullet_points = []
        if "coarse" in self._ol_currents:
            text += template.format(lens="coarse lens (OLc)",
                                    value=int(self._ol_currents["coarse"]))
            bullet_points.append(
                ("Coarse (OLc)", 
                 "0x{:x} (hex)".format(int(self._ol_currents["coarse"])), 
                 "{} (dec)".format(self._ol_currents["coarse"])))
            
            text += " and the "
            msg = "Currents are set"
        else:
            msg = "Current is set"
                                    
        text += template.format(lens="fine lens (OLf)",
                                value=int(self._ol_currents["fine"]))
        bullet_points.append(
            ("Fine (OLc)", 
             "0x{:x} (hex)".format(int(self._ol_currents["fine"])), 
             "{} (dec)".format(self._ol_currents["fine"])))
        
        text += ".\n\n"
        ll = 0 # the character length of the label column
        hl = 0 # the character length of the hex value column
        dl = 0 # the character length of the decimal value column
        for label, hexval, decval in bullet_points:
            ll = max(ll, len(label))
            hl = max(hl, len(hexval))
            dl = max(dl, len(decval))
        for label, hexval, decval in bullet_points:
            text += ("- {{:{}}}\t{{:>{}}}\t{{:>{}}}".format(ll, hl, dl)).format(
                label, hexval, decval) + "\n"
        
        text += "\nAfter confirming the measurement will be continued."
        
        if logginglib.do_log(self._logger, logging.DEBUG):
            self._logger.debug("Asking the user to set the coarse and fine " + 
                               "lens to the values '{}'".format(self._ol_currents))
        
        button = self.controller.view.askForDecision(text, options=(msg, "Cancel"))
        if button == 1:
            raise StopProgram
    
    def _getObjectiveLensCurrent(self) -> float:
        """Get the objective lense current in the current units.

        Returns
        -------
        float
            The actual current of the objective lense at the microscope,
            measured in objective fine lense steps
        """
        
        if "fine" in self._ol_currents:
            fine_value = self._ol_currents["fine"]
        else:
            raise IOError("The microscope cannot get the objective lens " + 
                          "current by the API and the current has not yet " + 
                          "been saved.")

        coarse_value = None
        if "coarse" in self._ol_currents:
            coarse_value = self._ol_currents["coarse"]

        if (isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)) and
            isinstance(coarse_value, (int, float)) and 
            self.objective_lense_coarse_fine_stepwidth > 0):
            value = (coarse_value * self.objective_lense_coarse_fine_stepwidth + 
                     fine_value)
        else:
            value = fine_value

        return value
    
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
    
    def _setObjectiveMiniLensCurrent(self, value: int) -> None:
        """Set the objective mini lens current to the given current value.
        
        The value is equal to the 'hex' value for the lens current but as an 
        integer. This also only works in LowMAG mode sice this uses the 
        `DigitalMicrograph.Py_Microscope.SetFocus()` which is directed to the 
        mini lens only in LowMAG mode.

        Raises
        ------
        RuntimeError
            When the microscope is not in the LowMag mode.

        Parameters
        ----------
        value : int
            The objectiv mini lens current value
        """
        if not self.getInLorentzMode():
            err = RuntimeError("The objective mini lens current (and " + 
                               "therefore the focus) can only beused if the " + 
                               "microscope is in the LowMAG mode. But the " + 
                               "microscope is not in the LowMag mode.")
            logginglib.log_error(self._logger, err)
            raise err
        
        self.dm_microscope.SetFocus(value)
        # self.dm_microscope.SetCalibratedFocus(value)
    
    def _getObjectiveMiniLensCurrent(self) -> int:
        """Get the objective mini lens current.
        
        The value is equal to the 'hex' value for the lens current but as an 
        integer. This also only works in LowMAG mode sice this uses the 
        `DigitalMicrograph.Py_Microscope.SetFocus()` which is directed to the 
        mini lens only in LowMAG mode.

        Raises
        ------
        RuntimeError
            When the microscope is not in the LowMag mode.

        Returns
        -------
        int
            The focus
        """
        if not self.getInLorentzMode():
            err = RuntimeError("The objective mini lens current (and " + 
                               "therefore the focus) can only beused if the " + 
                               "microscope is in the LowMAG mode. But the " + 
                               "microscope is not in the LowMag mode.")
            logginglib.log_error(self._logger, err)
            raise err
        
        return int(self.dm_microscope.GetFocus())
        # return self.dm_microscope.GetCalibratedFocus()

    def resetToSafeState(self) -> None:
        """Set the microscope into its safe state.

        The safe state will set the microscope not to be in lorentz mode anymore.
        In addition the stage is driven to its origin, with resolving the tilt 
        in all axes.

        This function blocks the `MicroscopeInterface.action_lock` while 
        operating.
        """

        if logginglib.do_log(self._logger, logging.DEBUG):
            self._logger.debug("Setting microscope to safe state")

        # reset the lorentz mode
        self.setInLorentzMode(False)

        # lock the microscope after the lorentz mode, otherwise there is a 
        # deadlock (this function blocks the lock, 
        # PyJEMMicroscope::setInLorentzMode() waits for the lock)
        self.action_lock.acquire()

        if self.dm_microscope.HasBeamBlanker():
            if logginglib.do_log(self._logger, logging.DEBUG):
                self._logger.debug("Blanking beam")
            
            self.dm_microscope.SetBeamBlanked(True)

        # release the lock, the setCurrentState() needs the lock again
        self.action_lock.release()
    
    @staticmethod
    def defineConfigurationOptions(configuration: "AbstractConfiguration", 
                                   config_group_name: typing.Optional[str]="pyjem-microscope",
                                   config_defaults: typing.Optional[dict]={}) -> None:
        """Define which configuration options this class requires.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration to define the required options in
        config_group_name : str, optional
            The group name this device should use to save persistent values in
            the configuration, this is given automatically when loading this
            object as a device, default: "pyjem-microscope"
        config_defaults : dict, optional
            The default values to use, this is given automatically when loading
            this object as a device, default: {}
        """
        
        # add the option for the calibration factor for the focus
        if not "focus-calibration" in config_defaults:
            config_defaults["focus-calibration"] = 0
        configuration.addConfigurationOption(
            config_group_name, 
            "focus-calibration", 
            datatype=float, 
            description=("The calibration factor for the focus. The " + 
            "focus set in the GUI will be divided by this factor to pass " + 
            "it to the PyJEM functions. The focus received by the PyJEM " + 
            "functions will be multiplied with this factor and then shown."), 
            restart_required=True,
            default_value=config_defaults["focus-calibration"]
        )
        
        # add the stepwidth of the objective coarse lense in objective fine 
        # lense units
        if not "objective-lense-coarse-fine-stepwidth" in config_defaults:
            config_defaults["objective-lense-coarse-fine-stepwidth"] = None
        configuration.addConfigurationOption(
            config_group_name, 
            "objective-lense-coarse-fine-stepwidth", 
            datatype=float, 
            description=("The factor to calculate between the fine and " + 
            "coarse objective lense. One step with the objective coarse " + 
            "value is equal to this value steps with the objective fine " + 
            "lense. So OL-fine * value = OL-coarse."), 
            restart_required=True,
            default_value=config_defaults["objective-lense-coarse-fine-stepwidth"]
        )
        
        # add the option for the calibration factor for the magnetic field
        if not "objective-lense-magnetic-field-calibration" in config_defaults:
            config_defaults["objective-lense-magnetic-field-calibration"] = 0
        configuration.addConfigurationOption(
            config_group_name, 
            "objective-lense-magnetic-field-calibration", 
            datatype=float, 
            description=("The calibration factor for the objective lense to " + 
            "set the magnetic field at the probe position. The calibration " + 
            "factor is defined as the magnetic field per current. The unit is " + 
            "then [magnetic field]/[current]."), 
            restart_required=True,
            default_value=config_defaults["objective-lense-magnetic-field-calibration"]
        )

        # add the option for the magnetic field unit to display
        if not "magnetic-field-unit" in config_defaults:
            config_defaults["magnetic-field-unit"] = ""
        configuration.addConfigurationOption(
            config_group_name, 
            "magnetic-field-unit", 
            datatype=str, 
            description=("The unit the magnetic field is measured in if the " + 
                "calibration factor is given."), 
            restart_required=True,
            default_value=config_defaults["magnetic-field-unit"]
        )