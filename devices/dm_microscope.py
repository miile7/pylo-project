import os
import copy
import glob
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

from pylo.config import MAX_LOOP_COUNT

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
        self._tolerances = {}

        # the factor to multiply the focus with to show it to the user, 
        # the user entered values will be divided by this factor and then 
        # passed to the PyJEM functions
        focus_calibration_factor = self.controller.configuration.getValue(
            self.config_group_name, "focus-calibration", datatype=float,
            default_value=None)

        if (not isinstance(focus_calibration_factor, (int, float)) or 
            math.isclose(focus_calibration_factor, 0)):
            focus_calibration_factor = None
        
        logginglib.log_debug(self._logger, "Focus calibration is '{}'".format(
                             focus_calibration_factor))
        
        # load the tolerance for the objective mini lens
        objective_mini_lens_tolerance = self.controller.configuration.getValue(
            self.config_group_name, "abs-wait-tolerance-objective-mini-lens", 
            datatype=Datatype.hex_int, default_value=None)

        if (isinstance(objective_mini_lens_tolerance, int) and 
            objective_mini_lens_tolerance != 0):
            self._tolerances["om-current"] = objective_mini_lens_tolerance
        
        logginglib.log_debug(self._logger, ("Objective mini lens waiting " +  
                             "tolerance is '{}'").format(
                             objective_mini_lens_tolerance))

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
        
        logginglib.log_debug(self._logger, "Asking the user to set the focus to 0")
        
        # GMS needs some time here, don't know why but this fixes the bug, if 
        # the sleeping is removed, the dialog will never show up but the 
        # program will wait for interaction so it freezes
        time.sleep(0.1)
        button = self.controller.view.askForDecision(("Please set the focus " + 
            "to zero manually now. This will be  saved as the reference value."),
            ("Focus is 0 now", "Cancel"))
        
        if button == 1:
            err = StopProgram()
            logginglib.log_debug(self._logger, "Stopping program", exc_info=err)
            raise err
        
        # the factor to get from the objective fine lense value to the 
        # objective coarse lense value
        self.objective_lense_coarse_fine_stepwidth = self.controller.configuration.getValue(
            self.config_group_name, 
            "objective-lense-coarse-fine-stepwidth", datatype=Datatype.int,
            fallback_default=None)
        
        if (not isinstance(self.objective_lense_coarse_fine_stepwidth, (int, float)) or 
            math.isclose(self.objective_lense_coarse_fine_stepwidth, 0)):
            self.objective_lense_coarse_fine_stepwidth = None
        
        logginglib.log_debug(self._logger, ("Objective fine-coarse lens stepwidth is " + 
                                "'{}'").format(
                                self.objective_lense_coarse_fine_stepwidth))

        # the factor to multiply the lense current with to get the magnetic
        # field
        magnetic_field_calibration_factor = self.controller.configuration.getValue(
            self.config_group_name, 
            "objective-lense-magnetic-field-calibration", datatype=float,
            default_value=None)
        
        if (not isinstance(magnetic_field_calibration_factor, (int, float)) or 
            math.isclose(magnetic_field_calibration_factor, 0)):
            magnetic_field_calibration_factor = None
        
        logginglib.log_debug(self._logger, "Magnetic field calibration factor is '{}'".format(
                               magnetic_field_calibration_factor))
        
        if magnetic_field_calibration_factor is not None:
            # the units of the magnetic field that results when multiplying with 
            # the magnetic_field_calibration_factor
            magnetic_field_unit = (self.controller.configuration.getValue(
                self.config_group_name, "magnetic-field-unit", 
                default_value=None))
        else:
            magnetic_field_unit = None
        
        logginglib.log_debug(self._logger, "Magnetic field unit is '{}'".format(
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

        # try to find idx files
        from pylo.config import PROGRAM_DATA_DIRECTORIES
        idx_dirs = copy.deepcopy(PROGRAM_DATA_DIRECTORIES)
        try:
            idx_dirs.append(os.path.dirname(__file__))
        except NameError:
            # __file__ does not exist
            pass
        
        if logginglib.do_log(self._logger, logging.INFO):
            self._logger.info("Searching *.idx files containing holder " + 
                              "definitions in directories:")
        
        idx_files = []
        for idx_dir in idx_dirs:
            if logginglib.do_log(self._logger, logging.INFO):
                self._logger.info("  {}".format(idx_dir))
            
            p = os.path.join(idx_dir, "*.idx")
            logginglib.log_debug(self._logger, "Searching files '{}'".format(p))
            idx_files += glob.glob(p)

            p = os.path.join(idx_dir, "*", "*.idx")
            logginglib.log_debug(self._logger, "Searching files '{}'".format(p))
            idx_files += glob.glob(p)
        
        logginglib.log_debug(self._logger, ("Found '{}' idx files: " + 
                             "'{}'").format(len(idx_files), idx_files))
        
        self.holders = {}
        for idx_file in idx_files:
            try:
                idx_file = IDXReader(idx_file)
            except ValueError as e:
                logginglib.log_error(self._logger, e)
             
            if idx_file.isValidHolderFile():
                logginglib.log_debug(self._logger, ("Found holder definition " + 
                                     "in file '{}' with holder '{}' '{}', " + 
                                     "'{}' <= x-tilt <= '{}' and '{}' " + 
                                     "<= y-tilt <= '{}'").format(
                                     idx_file.idx_path, idx_file.holder_number, 
                                     idx_file.holder_name, idx_file.min_x_tilt,
                                     idx_file.max_x_tilt, idx_file.min_y_tilt,
                                     idx_file.max_y_tilt))
                label = "{} ({})".format(idx_file.holder_name, 
                                         idx_file.holder_number)
                self.holders[label] = idx_file
            else:
                logginglib.log_debug(self._logger, ("Holder '{}' is " + 
                                     "invalid: '{}'.").format(idx_file,
                                     idx_file.getErrorMsgs()))
        
        logginglib.log_debug(self._logger, "Asking the user for the holder")

        installed_holder_label, *_ = self.controller.view.askFor({
            "name": "Installed holder",
            "datatype": Datatype.options(list(self.holders.keys())),
            "description": ("Please select the holder that is currently " + 
                            "installed and used for the measurement. If you " +
                            "want to use a different holder, change it now. " + 
                            "\n\n" + 
                            "Note that entering a wrong holder will " + 
                            "initialize the microscope wrong which may " + 
                            "cause damage.")
        })
        self.installed_holder = self.holders[installed_holder_label]
        
        logginglib.log_debug(self._logger, "User selected '{}' holder '{}'".format(
                             installed_holder_label, self.installed_holder))
        
        # tilt limits depend on holder
        variable = self.registerMeasurementVariable(
            MeasurementVariable("x-tilt", "X Tilt", 
                                self.installed_holder.min_x_tilt, 
                                self.installed_holder.max_x_tilt, "deg"),
            self._getXTilt,
            self._setXTilt
        )
        variable.default_start_value = 0
        variable.default_end_value = 10
        # variable.default_step_width_value = 

        # load the tolerance for the x tilt
        x_tilt_tolerance = self.controller.configuration.getValue(
            self.config_group_name, "abs-wait-tolerance-x-tilt", datatype=float,
            default_value=None)

        if (isinstance(x_tilt_tolerance, (int, float)) and 
            not math.isclose(x_tilt_tolerance, 0)):
            self._tolerances["x-tilt"] = x_tilt_tolerance
        
        logginglib.log_debug(self._logger, ("x tilt tolerance is '{}'").format(
                             x_tilt_tolerance))
    
        # load the tolerance for the y tilt
        y_tilt_tolerance = self.controller.configuration.getValue(
            self.config_group_name, "abs-wait-tolerance-y-tilt", datatype=float,
            default_value=None)

        if (isinstance(y_tilt_tolerance, (int, float)) and 
            not math.isclose(y_tilt_tolerance, 0)):
            self._tolerances["y-tilt"] = y_tilt_tolerance
        
        logginglib.log_debug(self._logger, ("y tilt tolerance is '{}'").format(
                             y_tilt_tolerance))

        self.holder_confirmed = True
        if (self.installed_holder.min_y_tilt < 1 and 
            self.installed_holder.max_y_tilt > 1):
            self.registerMeasurementVariable(
                MeasurementVariable("y-tilt", "Y Tilt", 
                                    self.installed_holder.min_y_tilt, 
                                    self.installed_holder.max_y_tilt, "deg"),
                self._getYTilt,
                self._setYTilt
            )
            # extra ask for the user if the tilt holder really is installed, 
            # just to be extra sure
            self.holder_confirmed = False
        microscope_ready.append(self._confirmHolder)

        from pylo.config import OFFLINE_MODE

        if DM is not None and not OFFLINE_MODE:
            logginglib.log_debug(self._logger, "Creating DigitalMicrograph.Py_Microscope")
            self.dm_microscope = DM.Py_Microscope()
        else:
            self.dm_microscope = None
    
    def _confirmHolder(self, *args) -> None:
        """Show a confirm dialog with the view if the holder is not yet
        confirmed.

        Raises
        ------
        StopProgram
            If the user clicks 'cancel'
        """

        if not self.holder_confirmed:
            logginglib.log_debug(self._logger, ("Asking user to confirm '{}' " + 
                                 "holder").format(self.installed_holder))
                                   
            button = self.controller.view.askForDecision(
                ("Please confirm, that the probe holder '{}' ({}) really is " + 
                 "installed at the microscope.").format(
                 self.installed_holder.holder_name, 
                 self.installed_holder.holder_number),
                ("Yes, it is installed", "Cancel"))
            
            if button == 0:
                logginglib.log_debug(self._logger, "'{}' holder is confirmed".format(
                                     self.installed_holder))
                                    
                self.holder_confirmed = True
            else:
                err = StopProgram()
                logginglib.log_debug(self._logger, "Holder rejected, " + 
                                     "stopping program", exc_info=err)
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
            
            logginglib.log_debug(self._logger, ("Setting microscope to lorentz mode by " + 
                                    "EMControl.dll (mode = '{}') with " + 
                                    "dmscript '{}'").format(
                                    IMAGING_OPTICS_MODE_GIF_LowMAG, dmscript))

            with execdmscript.exec_dmscript(dmscript):
                pass
        else:
            logginglib.log_debug(self._logger, "Asking the user to set the microscope " + 
                                   "into lorentz mode manually")
            
            self.controller.view.askForDecision("Please set the microscope " + 
                                                "into the lorentz mode.", 
                                                options=("In lorentz mode now", 
                                                         "Cancel"))

            logginglib.log_debug(self._logger, "User confirmed that the microscope is " + 
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
            logginglib.log_debug(self._logger, "Checking if the microscope is in lorentz " + 
                                   "mode")
            
            lorentz = (self.dm_microscope.GetImagingOpticsMode() == 
                       IMAGING_OPTICS_MODE_LowMAG)

            logginglib.log_debug(self._logger, "Microscope returned '{}'".format(lorentz))
            
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
        
        value = float(value)
        
        if ("value" in self._ol_currents and 
            math.isclose(self._ol_currents["value"], value)):
            # value is still the same from the last time
            logginglib.log_debug(self._logger, ("Setting objectiv lens " + 
                                 "current to '{}' but the current value is " + 
                                 "'{}', so the function is now skipped").format(
                                    value, self._ol_currents["value"]))
            
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
        
        var = self.getMeasurementVariableById("ol-current")
        if var.has_calibration:
            if var.calibrated_name is not None:
                name = var.calibrated_name
            else:
                name = var.name
            if var.calibrated_unit is not None:
                unit = var.calibrated_unit
            else:
                unit = var.unit
            
            calibrated_text = " to reach a {} of {:.2f}{}".format(name, 
                                var.convertToCalibrated(value), unit)
        else:
            calibrated_text = ""
        
        # tell the operator to set the values manually
        template = "{lens} value to '0x{value:x}' (decimal: '{value}')"
        text = ("Please change the objectiv lens current manually{}. Set " + 
                "the ").format(calibrated_text)
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
        
        logginglib.log_debug(self._logger, "Asking the user to set the coarse and fine " + 
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

        # block until the value is reached
        self._waitForVariableValue("x-tilt", self._getXTilt, value)
    
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

        # block until the value is reached
        self._waitForVariableValue("y-tilt", self._getYTilt, value)
    
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

        # block until the value is reached
        self._waitForVariableValue("om-current", 
                                   self._getObjectiveMiniLensCurrent, value)
    
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
    
    def _waitForVariableValue(self, id_: str, getter: typing.Callable, 
                              value: typing.Any, 
                              sleep_time: typing.Optional[typing.Union[float, int]]=0.1) -> None:
        """Wait for the variable with the `id_` to reach the `value`.

        If there is no entry for the `id_` in the `DMMicroscope._tolerances`, 
        the function will return immediately. Otherwise the thread is blocked 
        until the `getter` returns a value close to the desired `value`. If not
        the function will raise a RuntimeError after 
        `pylo.config.MAX_LOOP_COUNT * sleep_time` seconds.

        Raises
        ------
        RuntimeError
            When the `value` is not reached after a specified amount of time
        
        Parameters
        ----------
        id_ : str
            The id of the measurement variable, needs to have an int or float
            value with the same key in the `DMMicroscope._tolerances`
        getter : callable
            The getter callback to get the actual value from the microscope
        sleep_time : float or int, optional
            The number of seconds to wait between asking the microscope again
            what the actual value is, default: 0.1
        """
        if (id_ in self._tolerances and 
            isinstance(self._tolerances[id_], (int, float))):

            logginglib.log_debug(self._logger, ("Waiting until '{}' '{}' is " + 
                                 "reached").format(id_, value))

            v = None
            security_counter = 0
            while security_counter < MAX_LOOP_COUNT:
                v = getter()
                if math.isclose(v, value, abs_tol=self._tolerances[id_]):
                    break
                
                security_counter += 1
                time.sleep(0.1)
            
            if security_counter + 1 == MAX_LOOP_COUNT:
                err = RuntimeError(("The microscope was told to set the " + 
                                    "'{}' to '{}' but after '{}' times " + 
                                    "trying plus waiting the value is '{}' " + 
                                    "which is not in the tolerance of '{}'. " + 
                                    "Either the microscope takes extremely " + 
                                    "long to reach the value, there is a " + 
                                    "problem with the communication or the " + 
                                    "waiting count '{}' is very low.").format(
                                    id_, value, security_counter, v, 
                                    self._tolerances[id_], MAX_LOOP_COUNT))
                logginglib.log_error(self._logger, err)
                raise err
            else:
                logginglib.log_debug(self._logger, ("Reached value '{}' for " + 
                                     "'{}' after '{}' runs (='{}' " + 
                                     "seconds)").format(v, id_, 
                                     security_counter, 
                                     sleep_time * security_counter))

    def resetToSafeState(self) -> None:
        """Set the microscope into its safe state.

        The safe state will set the microscope not to be in lorentz mode anymore.
        In addition the stage is driven to its origin, with resolving the tilt 
        in all axes.

        This function blocks the `MicroscopeInterface.action_lock` while 
        operating.
        """

        logginglib.log_debug(self._logger, "Setting microscope to safe state")

        # reset the lorentz mode
        self.setInLorentzMode(False)

        # lock the microscope after the lorentz mode, otherwise there is a 
        # deadlock (this function blocks the lock, 
        # PyJEMMicroscope::setInLorentzMode() waits for the lock)
        self.action_lock.acquire()

        if self.dm_microscope.HasBeamBlanker():
            logginglib.log_debug(self._logger, "Blanking beam")
            
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

        # add the option for the x tilt tolerance
        if not "abs-wait-tolerance-x-tilt" in config_defaults:
            config_defaults["abs-wait-tolerance-x-tilt"] = 1
        configuration.addConfigurationOption(
            config_group_name, 
            "abs-wait-tolerance-x-tilt", 
            datatype=float, 
            description=("When the microscope is told to set the x tilt, the " + 
                         "program will wait until the real value at the " + 
                         "microscope is the desired value +/- this tolerance." + 
                         "Note that it must not be 0 sice the sensors are " + 
                         "not that precise. The microscope will never return " + 
                         "the same value as it is set to. The tolerance is " + 
                         "given in degrees."), 
            restart_required=False,
            default_value=config_defaults["abs-wait-tolerance-x-tilt"]
        )

        # add the option for the y tilt tolerance
        if not "abs-wait-tolerance-y-tilt" in config_defaults:
            config_defaults["abs-wait-tolerance-y-tilt"] = 1
        configuration.addConfigurationOption(
            config_group_name, 
            "abs-wait-tolerance-y-tilt", 
            datatype=float, 
            description=("When the microscope is told to set the y tilt, the " + 
                         "program will wait until the real value at the " + 
                         "microscope is the desired value +/- this tolerance." + 
                         "Note that it must not be 0 sice the sensors are " + 
                         "not that precise. The microscope will never return " + 
                         "the same value as it is set to. The tolerance is " + 
                         "given in degrees."), 
            restart_required=False,
            default_value=config_defaults["abs-wait-tolerance-y-tilt"]
        )

        # add the option for the mini lens tolerance
        if not "abs-wait-tolerance-objective-mini-lens" in config_defaults:
            config_defaults["abs-wait-tolerance-objective-mini-lens"] = 0x2
        configuration.addConfigurationOption(
            config_group_name, 
            "abs-wait-tolerance-objective-mini-lens", 
            datatype=Datatype.hex_int, 
            description=("When the microscope is told to set the focus (= the " + 
                         "objective mini lens current), the program will wait " + 
                         "until the real value at the microscope is the " + 
                         "desired value +/- this tolerance. The tolerance is " + 
                         "given in hex value."), 
            restart_required=False,
            default_value=config_defaults["abs-wait-tolerance-objective-mini-lens"]
        )

class IDXReader:
    """A reader to read out JEOL idx files that contain holder data.

    Attributes
    ----------
    holder_number : str
        The id number of the holder, read only
    holder_name : str
        The name of the holder, read only
    min_x_tilt : float
        The minimum x tilt in degrees, read only
    max_x_tilt : float
        The maximum x tilt in degrees, read only
    min_y_tilt : float
        The minimum y tilt in degrees, read only
    max_y_tilt : float
        The maximum y tilt in degrees, read only
    """
    # data in the lines, key is the attribute name of the IDXReader instance,
    # the first value in the value tuple is the (zero-based) line number, 
    # the second is the datatype (as type or pylo.Datatype), the third 
    # (optional) value is a callback that is performed on each parsing, first 
    # and only parameter is the line data in the given datatype
    line_data = {
        "holder_number": (0, str),
        "holder_name": (1, str),
        "min_x_tilt": (11, float, lambda x: x / 100),
        "max_x_tilt": (14, float, lambda x: x / 100),
        "min_y_tilt": (17, float, lambda x: x / 100),
        "max_y_tilt": (20, float, lambda x: x / 100)
    }
    
    def __init__(self, idx_path: typing.Union[pylolib.path_like]) -> None:
        """Create the idx reader for the give `idx_path`.

        Parameters
        ----------
        idx_path : path_like
            The path to the idx file (with the extension)
        """
        if not os.path.exists(idx_path) or not os.path.isfile(idx_path):
            raise FileExistsError("The file '{}' does not exist".format(idx_path))
            
        self.idx_path = idx_path
        self._idx_cache = {}
    
    def isValidHolderFile(self) -> bool:
        """Return whether the file can be read as a holder file.

        Returns
        -------
        bool
            True if the file has the structure of a holder file, false if not.
        """
        return self.getErrorCode() == 0
    
    def getErrorCode(self) -> int:
        """Get the error code.

        The returned value is a bit mask of the following:

        - 0b000001: if the holder name is invalid
        - 0b000010: if the holder number is invalid
        - 0b000100: if the min x tilt is invalid
        - 0b001000: if the max x tilt is invalid
        - 0b001000: if the min y tilt is invalid
        - 0b010000: if the max y tilt is invalid
        - 0b100000: if a ValueError is raised during checking

        Returns
        -------
        int
            The bitmask of the errors or 0 if there is no error
        """
        errors, error_msgs = self._getErrors()
        return errors
    
    def getErrorMsgs(self) -> typing.List[str]:
        """Get the errors as a list of readable messages.

        Returns
        -------
        list of str
            A list of all error messages
        """
        errors, error_msgs = self._getErrors()
        return error_msgs
    
    def _getErrors(self) -> typing.Tuple[int, typing.List[str]]:
        """Get the errors that make this file not being a valid holder file.

        Returns
        -------
        int, list of str
            The errors as an integer and as a list of messages
        """

        errors = 0
        error_msgs = []

        try:
            if not isinstance(self.holder_name, str) or self.holder_name == "":
                errors |= 0b000001
                error_msgs.append("The holder name is not a str or empty")
            
            if (not isinstance(self.holder_number, str) or self.holder_number == ""):
                errors |= 0b000010
                error_msgs.append("The holder number is not a str or empty")
            
            if (not isinstance(self.min_x_tilt, (int, float)) or 
                self.min_x_tilt < -180):
                errors |= 0b000100
                error_msgs.append("The min x tilt neither is an int nor a " + 
                                  "float or less than -180")
            
            if (not isinstance(self.max_x_tilt, (int, float)) or 
                self.min_x_tilt > 180):
                errors |= 0b001000
                error_msgs.append("The max x tilt neither is an int nor a " + 
                                  "float or greater than 180")
            
            if (not isinstance(self.min_y_tilt, (int, float)) or 
                self.min_y_tilt < -180):
                errors |= 0b010000
                error_msgs.append("The min y tilt neither is an int nor a " + 
                                  "float or less than -180")
            
            if (not isinstance(self.max_y_tilt, (int, float)) or 
                self.min_y_tilt > 180):
                errors |= 0b100000
                error_msgs.append("The max y tilt neither is an int nor a " + 
                                  "float or greater than 180")
        except ValueError as e:
            errors |= 0b1000000
            error_msgs.append("{}: {}".format(e.__class__.__name__, str(e)))
        
        return errors, error_msgs
    
    def _get_line_data(self, line: int) -> typing.Any:
        """Get the data of the line with the number `line` and return it.

        Parameters
        ----------
        line : int
            The zero-based line number
        
        Returns
        -------
        any
            The line data
        """
        if line in self._idx_cache:
            return self._idx_cache[line]

        cache_lines = [d[0] for d in IDXReader.line_data.values()]

        with open(self.idx_path) as f:
            for i, l in enumerate(f):
                if i in cache_lines:
                    self._idx_cache[i] = l
                
                if i == line:
                    return l
        
        raise ValueError("The line '{}' is never reached.".format(line))
    
    def __getattribute__(self, name: str) -> typing.Any:
        """Get the attribute with the given `name`.

        This function emulates getting the lines defined by the 
        `IDXReader.line_data` as attributes directly.

        Raises
        ------
        AttributeError
            When the `name` attribute does not exist

        Parameters
        ----------
        name : str
            The attribute to get
        
        Returns
        -------
        any
            The attribute value
        """
        if name in IDXReader.line_data:
            # get the (cached) line data
            data = self._get_line_data(IDXReader.line_data[name][0])
            data = data.strip()

            # parse to the datatype
            if (len(IDXReader.line_data[name]) > 1 and 
                isinstance(IDXReader.line_data[name][1], (type, Datatype))):
                data = IDXReader.line_data[name][1](data)

            # perform a callback
            if (len(IDXReader.line_data[name]) > 2 and 
                callable(IDXReader.line_data[name][2])):
                data = IDXReader.line_data[name][2](data)
            
            return data
        else:
            return super().__getattribute__(name)
    
    def __setattr__(self, name: str, value: typing.Any) -> None:
        """Set the attribute.

        This function prevens writing the names defined in the 
        `IDXReader.line_data`.

        Parameters
        ----------
        name : str
            The attribute to set
        value : any
            The value
        """
        if name in IDXReader.line_data:
            raise AttributeError("The attribute '{}' is not settable.".format(name))
        else:
            super().__setattr__(name, value)
    
    def __delattr__(self, name: str) -> None:
        """Delete the attribute.

        This function prevens deleting the names defined in the 
        `IDXReader.line_data`.

        Parameters
        ----------
        name : str
            The attribute to set
        """
        if name in IDXReader.line_data:
            raise AttributeError("The attribute '{}' is not deletable.".format(name))
        else:
            super().__delattr__(name)
            
    
    def __dir__(self) -> list:
        """Get the names of all attributes
        
        Returns
        -------
        list
            The  name of all defined attribtues
        """
        return super().__dir__() + list(IDXReader.line_data.keys())

    def __repr__(self) -> str:
        """Get the representation of this file"""

        return "IDXReader('{}'/'{}', file: '{}')".format(self.holder_name, 
                                                         self.holder_number,
                                                         self.idx_path)   