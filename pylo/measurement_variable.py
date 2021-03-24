import math
import logging
import typing

from .logginglib import log_debug
from .logginglib import log_error
from .datatype import Datatype
from .logginglib import get_logger

class MeasurementVariable:
    """A physical variable that can be changed.

    This class represents variables that can be changed and observed by the 
    microscope. Typically this is the focus, the magnetic field (via the 
    objective lense), the tilt of the specimen ect.

    This supports calibration factors. The "calibrated value" in the following 
    is the value that can be used after the calibration is set 
    (`calibrated_name`, e.g. magnetic field). The "uncalibrated value" is the 
    original value the microscope uses internally which mostly is a current
    value or a voltage (`name`, e.g. objective lense current).
    
    The calibration (factor) will then calculate from the uncalibrated (lense 
    current) to the calibrated (magnetic field) value by multiplication. The 
    uncalibration (factor) is the opposite: Multiplying it with the 
    uncalibrated value (lense current) will return in the calibrated value 
    (magnetic field).

    So as a short example:
    ```
    <calibrated value> = <uncalibrated value> * calibration
    <uncalibrated value> = <calibrated value> * uncalibration

    so with <magnetic field> = Calibrated; <lense current> = Uncalibrated
    
    <magnetic field> = <lense current> * calibration
    <lense current> = <magnetic field> * uncalibration
    ```

    If there is no special name for the calibrated value but just a factor to 
    correct the value, use `calibration_name=None`. Same goes for the unit
    (even though it is recommended to somehow state that this is a different 
    unit now).

    Attributes
    ----------
    unique_id : str
        A unique id that defines this measurement variable, use lower ASCII 
        only, use minus (-) instead of spaces, must not start with numbers
    name : str
        The name of the value the microscope modifies
    min_value : float or None
        The minimum (uncalibrated) value that is allowed or None to allow any 
        value
    max_value : float or None
        The maximum (uncalibrated) value that is allowed or None to allow any 
        value
    unit : str or None
        The unit this measurement variable is expressed in, None for no unit
    format : Datatype or type
        A Datatype or type to format the input and output
    has_calibration : bool
        Whether there is a calibration factor (or function) that can calculate
        between two systems
    calibrated_unit : str or None, optional
        The units of the calibrated system, None for no unit
    calibrated_name : str or None, optional
        The name of the calibrated system if there is one, None for no name
    calibration_format : type, Datatype or None
        A Datatype or type to format the input and output
    default_start : float or None
        The default start value when a new series is created as the 
        uncalibrated value
    default_step_width : float or None
        The default step width value when a new series is created as the 
        uncalibrated value
    default_end : float or None
        The default end value when a new series is created as the uncalibrated
        value
    """

    def __init__(self, unique_id: str, name: str, 
                 min_value: typing.Optional[float]=None, 
                 max_value: typing.Optional[float]=None, 
                 unit: typing.Optional[str]=None,
                 format : typing.Optional[typing.Union[type, "Datatype"]]=float,
                 calibration: typing.Optional[typing.Union[int, float, typing.Callable[[typing.Union[int, float, str]], typing.Union[int, float, str]]]]=None,
                 uncalibration: typing.Optional[typing.Union[int, float, typing.Callable[[typing.Union[int, float, str]], typing.Union[int, float, str]]]]=None,
                 calibrated_unit: typing.Optional[str]=None,
                 calibrated_name: typing.Optional[str]=None,
                 calibrated_min: typing.Optional[float]=None,
                 calibrated_max: typing.Optional[float]=None,
                 calibrated_format : typing.Optional[typing.Union[type, "Datatype"]]=float):
        """Create a MeasurementVariable.

        Raises
        ------
        TypeError, ValueError
            When the calibration and uncalibration are of an invalid type or 
            invalid type
        ZeroDivisionError
            When the calibration or uncalibration are equal to zero

        Parameters
        ----------
        unique_id : str
            The string to identify this measurement variable, use lower ASCII 
            only, use minus (-) instead of spaces, must not start with numbers
        name : str
            The name to show in the GUI
        min_value : float, optional
            The minimum value that is allowed or None to allow any value
        max_value : float, optional
            The maximum value that is allowed or None to allow any value
        unit : str, optional
            The unit this measurement variable is expressed in, None for no 
            unit
        format : Datatype, or type, optional
            A Datatype or a type that formats the output (and in the first 
            case also the input) format or a type that can be used for the 
            input and the default python `format` function will be used for the 
            output formatting, this is for the uncalibrated value (if there is 
            a calibration), uncalibrated values gets passed to the microscope, 
            default: float
        calibration, uncalibration : int or float or callable, optional
            A calibration (multiplication) factor or a function to calculate 
            from the uncalibrated value to the calibrated, if one of them is 
            a number, the other one is the reciprocal so it does not have to be 
            given, if a callable is used, both have to be given, both have to
            be of the same type, `<calibrated value> = <uncalibrated value> * 
            calibration` and the other way around, the uncalibrated value will 
            be directly passed to the microscope, the calibrated value will be 
            shown to the user
        calibrated_unit : str, optional
            The unit the uncalibrated value is measured in, if None no unit 
            is used, ignored if there is no `calibration` given
        calibrated_name : str
            The name of the uncalibrated value if there is a name, ignored if
            there is no `calibration` given
        calibrated_min, uncalibrated_max : float, optional
            The minimum and maximum value of the uncalibrated value, this 
            should be equal to the `min_value` or the `max_value` but in the 
            other units, if not the maximum or the minimum (max for `min_value`,
            min for `max_value`) of both is saved, note that the `min_value` 
            or the `max_value` do not have to be given, this is intended to 
            set the min and max if the limits are in the uncalibrated space
        calibration_format : Datatype or type, optional
            A type, Datatype or a type that formats the output and 
            optinonally the input for the calibrated value, in the same way as
            the normal `format` parameter, the calibrated value will be shown
            to the user, default: float
        """
        self._logger = get_logger(self, instance_args=(unique_id, name))
        self.unique_id = unique_id
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit
        self.default_start_value = self.min_value
        self.default_end_value = self.max_value
        if (isinstance(self.default_start_value, (int, float)) and 
            isinstance(self.default_end_value, (int, float))):
            self.default_step_width_value = round((self.default_end_value - 
                                                   self.default_start_value) / 5, 
                                                   2)
        else:
            self.default_step_width_value = None
        
        self.format = format

        if (callable(calibration) and 
            callable(uncalibration)):
            self._calibration = calibration
            self._uncalibration = uncalibration
            self.has_calibration = True
            log_debug(self._logger, "Setting calibration and uncalibration to " + 
                                   "callback functions")
        elif callable(calibration):
            err = ValueError("The calibration is a callable but the " + 
                             "uncalibration is not. Either both or none " + 
                             "of the values can be a callable.")
            log_error(self._logger, err)
            raise err
        elif callable(uncalibration):
            err = ValueError("The uncalibration is a callable but the " + 
                             "calibration is not. Either both or none " + 
                             "of the values can be a callable.")
            log_error(self._logger, err)
            raise err
        elif isinstance(calibration, (int, float)) and calibration != 0:
            self._calibration = calibration
            self._uncalibration = 1 / calibration
            self.has_calibration = True
            log_debug(self._logger, ("Setting calibration to '{}', " + 
                                    "uncalibration is the reciprocal '{}'").format(
                                    self._calibration, self._uncalibration))
        elif isinstance(uncalibration, (int, float)) and uncalibration != 0:
            self._calibration = 1 / uncalibration
            self._uncalibration = uncalibration
            self.has_calibration = True
            log_debug(self._logger, ("Setting uncalibration to '{}', " + 
                                    "calibration is the reciprocal '{}'").format(
                                    self._uncalibration, self._calibration))
        elif calibration is not None or uncalibration is not None:
            err = TypeError(("The calibration and the uncalibration have to " + 
                             "either be both callables or one of them has to " + 
                             "be a number but the calibration is '{}' and the " + 
                             "uncalibration is '{}'.").format(calibration,
                                                              uncalibration))
            log_error(self._logger, err)
            raise err
        else:
            # no calibration given
            self.has_calibration = False
        
        if self.has_calibration:
            # fix the min value if necessary
            if isinstance(calibrated_min, (int, float)):
                if isinstance(self.min_value, (int, float)):
                    self.min_value = max(self.min_value, self.convertToUncalibrated(
                        calibrated_min
                    ))
                else:
                    self.min_value = self.convertToUncalibrated(calibrated_min)
            
            # fix the max value if necessary
            if isinstance(calibrated_max, (int, float)):
                if isinstance(self.max_value, (int, float)):
                    self.max_value = min(self.max_value, self.convertToUncalibrated(
                        calibrated_max
                    ))
                else:
                    self.max_value = self.convertToUncalibrated(calibrated_max)
            
            self.calibrated_name = calibrated_name
            self.calibrated_unit = calibrated_unit
            
            if isinstance(calibrated_format, (type, Datatype)):
                self.calibrated_format = calibrated_format
            else:
                self.calibrated_format = self.format
        else:
            self.calibrated_name = None
            self.calibrated_unit = None
            self.calibrated_format = None
        
    def convertToCalibrated(self, uncalibrated_value: typing.Union[int, float],
                            key: typing.Optional[str]=None) -> typing.Union[int, float]:
        """Convert the `uncalibrated_value` to a calibrated value.

        If there is no calibration given, the same value is returned.

        Parameters
        ----------
        uncalibrated_value : int or float
            The uncalibrated value
        
        Returns
        -------
        int or float
            The calibrated value
        """

        if self.has_calibration:
            if callable(self._calibration):
                return self._calibration(uncalibrated_value, key)
            elif isinstance(self._calibration, (int, float)):
                return uncalibrated_value * self._calibration
        
        return uncalibrated_value
        
    def convertToUncalibrated(self, calibrated_value: typing.Union[int, float],
                              key: typing.Optional[str]=None) -> typing.Union[int, float]:
        """Convert the `calibrated_value` to a uncalibrated value.

        If there is no uncalibration given, the same value is returned.

        Parameters
        ----------
        calibrated_value : int or float
            The calibrated value
        
        Returns
        -------
        int or float
            The uncalibrated value
        """

        if self.has_calibration:
            if callable(self._uncalibration):
                return self._uncalibration(calibrated_value, key)
            elif isinstance(self._uncalibration, (int, float)):
                return calibrated_value * self._uncalibration
        
        return calibrated_value
    
    def ensureCalibratedValue(self, value: typing.Union[int, float, None],
                              key: typing.Optional[str]=None) -> typing.Union[int, float, None]:
        """Return the calibrated `value` if there is a calibration, otherwise
        return the `value`.

        Parameters
        ----------
        value : int, float or None
            The (uncalibrated) value or None
        
        Returns
        -------
        int, float or None
            The calibrated value if there is a calibration or the `value` if 
            there is no calibration or None if the `value` is None
        """

        if not isinstance(value, (int, float)):
            return value

        if self.has_calibration:
            return self.convertToCalibrated(value, key)
        else:
            return value
    
    def ensureUncalibratedValue(self, value: typing.Union[int, float, None],
                                key: typing.Optional[str]=None) -> typing.Union[int, float, None]:
        """Return the uncalibrated `value` if there is a calibration, otherwise
        return the `value`.

        Parameters
        ----------
        value : int, float or None
            The (calibrated) value or None
        
        Returns
        -------
        int, float or None
            The uncalibrated value if there is a calibration or the `value` if 
            there is no calibration or None if the `value` is None
        """

        if not isinstance(value, (int, float)):
            return value

        if self.has_calibration:
            return self.convertToUncalibrated(value, key)
        else:
            return value