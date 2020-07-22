import typing
import math

class MeasurementVariable:
    """A physical variable that can be changed.

    This class represents variables that can be changed and observed by the 
    microscope. Typically this is the focus, the magnetic field (via the 
    objective lense), the tilt of the specimen ect.

    This supports calibration factors. Calibration in the following means the 
    value this represents (the name, e.g. the magnetic field). The 
    uncalibration is the underlaying value that is acutally modified (the 
    uncalibrated name if given, mostly a voltage or current, e.g. the 
    objective lense current). The calibration (factor) will then calculate from 
    the uncalibrated (lense current) to the calibrated (magnetic field) value 
    by multiplication. The uncalibration (factor) is the opposite: Multiplying
    it with the uncalibrated value (lense current) will return in the 
    calibrated value (magnetic field).

    So as a short example:
    ```
    <magnetic field> = Calibrated; <lense current> = Uncalibrated
    
    <magnetic field> = <lense current> * calibration
    <lense current> = <magnetic field> * uncalibration
    ```

    In most cases there is no `uncalibrated_name` but just a factor. In this 
    case simply leave the `uncalibrated_name=None`. Same goes for the unit.

    Attributes
    ----------
    unique_id : str
        A unique id that defines this measurement variable, use lower ASCII 
        only, use minus (-) instead of spaces, must not start with numbers
    name : str
        The name to show in the GUI
    min_value : float or None
        The minimum value that is allowed or None to allow any value
    max_value : float or None
        The maximum value that is allowed or None to allow any value
    unit : str or None
        The unit this measurement variable is expressed in, None for no unit
    has_calibration : bool
        Whether there is a calibration factor (or function) that can calculate
        between two systems
    uncalibrated_unit : str or None
        The units of the uncalibrated system, None for no unit
    uncalibrated_name : str or None
        The name of the uncalibrated system if there is one, None for no name
    """

    def __init__(self, unique_id: str, name: str, 
                 min_value: typing.Optional[float]=None, 
                 max_value: typing.Optional[float]=None, 
                 unit: typing.Optional[str]=None,
                 calibration: typing.Optional[typing.Union[int, float, callable]]=None,
                 uncalibration: typing.Optional[typing.Union[int, float, callable]]=None,
                 uncalibrated_unit: typing.Optional[str]=None,
                 uncalibrated_name: typing.Optional[str]=None,
                 uncalibrated_min: typing.Optional[float]=None,
                 uncalibrated_max: typing.Optional[float]=None):
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
        calibration, uncalibration : int or float or callable, optional
            A calibration (multiplication) factor or a function to calculate 
            from the uncalibrated value to the calibrated, if one of them is 
            a number, the other one is the reciprocal so it does not have to be 
            given, if a callable is used, both have to be given, both have to
            be of the same type
        uncalibrated_unit : str, optional
            The unit the uncalibrated value is measured in, if None no unit 
            is used, ignored if there is no `calibration` given
        uncalibrated_name : str
            The name of the uncalibrated value if there is a name, ignored if
            there is no `calibration` given
        uncalibrated_min, uncalibrated_max : float, optional
            The minimum and maximum value of the uncalibrated value, this 
            should be equal to the `min_value` or the `max_value` but in the 
            other units, if not the maximum or the minimum (max for `min_value`,
            min for `max_value`) of both is saved, note that the `min_value` 
            or the `max_value` do not have to be given, this is intended to 
            set the min and max if the limits are in the uncalibrated space
        """
        self.unique_id = unique_id
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit

        if (callable(calibration) and 
            callable(uncalibration)):
            self._calibration = calibration
            self._uncalibration = uncalibration
            self.has_calibration = True
        elif callable(calibration):
            raise ValueError("The calibration is a callable but the " + 
                             "uncalibration is not. Either both or none " + 
                             "of the values can be a callable.")
        elif callable(uncalibration):
            raise ValueError("The uncalibration is a callable but the " + 
                             "calibration is not. Either both or none " + 
                             "of the values can be a callable.")
        elif isinstance(calibration, (int, float)):
            self._calibration = calibration
            self._uncalibration = 1 / calibration
            self.has_calibration = True
        elif isinstance(uncalibration, (int, float)):
            self._calibration = 1 / uncalibration
            self._uncalibration = uncalibration
            self.has_calibration = True
        elif calibration is not None or uncalibration is not None:
            raise TypeError("The calibration and the uncalibration have to " + 
                            "either be both callables or one of them has to " + 
                            "be a number.")
        else:
            # no calibration given
            self.has_calibration = False
        
        if self.has_calibration:
            # fix the min value if necessary
            if isinstance(uncalibrated_min, (int, float)):
                if isinstance(self.min_value, (int, float)):
                    self.min_value = max(self.min_value, self.convertToCalibrated(
                        uncalibrated_min
                    ))
                else:
                    self.min_value = self.convertToCalibrated(uncalibrated_min)
            
            # fix the max value if necessary
            if isinstance(uncalibrated_max, (int, float)):
                if isinstance(self.max_value, (int, float)):
                    self.max_value = min(self.max_value, self.convertToCalibrated(
                        uncalibrated_max
                    ))
                else:
                    self.max_value = self.convertToCalibrated(uncalibrated_max)
            
            self.uncalibrated_name = uncalibrated_name
            self.uncalibrated_unit = uncalibrated_unit
        else:
            self.uncalibrated_name = None
            self.uncalibrated_unit = None
        
    def convertToCalibrated(self, uncalibrated_value: typing.Union[int, float]) -> typing.Union[int, float]:
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
                return self._calibration(uncalibrated_value)
            elif isinstance(self._calibration, (int, float)):
                return uncalibrated_value * self._calibration
        
        return uncalibrated_value
        
    def convertToUncalibrated(self, calibrated_value: typing.Union[int, float]) -> typing.Union[int, float]:
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
                return self._uncalibration(calibrated_value)
            elif isinstance(self._uncalibration, (int, float)):
                return calibrated_value * self._uncalibration
        
        return calibrated_value