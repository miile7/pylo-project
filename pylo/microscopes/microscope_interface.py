import typing
import threading

from ..vulnerable_machine import VulnerableMachine

class MicroscopeInterface(VulnerableMachine):
    """
    An interface class to communicate with the microscope.

    Attributes
    ----------
    controller : Controller
        The controller
    supported_measurement_variables : list of MeasurementVariable
        All the measurement variables that this microscope supports, typically 
        this is the magnetic field (via controlling the lens current of the 
        objective lense or any lense that is close/around the speciemen), the 
        focus and possibly the tilt of the speciemen
    supports_parallel_measurement_variable_setting : bool
        Whether `MeasurementVariable`s can be set parallel, for example the 
        tilt can be set while the lense current is set
    action_lock : bool
        A lock that is used to prevent setting multiple measurement variables
        at the same time if 
        `MicroscopeInterface.supports_parallel_measurement_variable_setting` is
        False
    """

    def __init__(self, controller : "Controller") -> None:
        """Get the microscope instance"""
        self.supported_measurement_variables = []
        self.supports_parallel_measurement_variable_setting = True
        self.controller = controller
        self._measurement_variable_getter_setter_map = {}

        # a lock so only one action can be performed at once at the microscope
        self.action_lock = threading.Lock()
    
    def registerMeasurementVariable(self, variable: "MeasurementVariable", 
                                    getter: typing.Callable[["MicroscopeInterface"], typing.Union[int, float, str]], 
                                    setter: typing.Callable[["MicroscopeInterface", typing.Union[int, float, str]], None]) -> None:
        """Register a `MeasurementVariable` so this microscope knows that it 
        can change this parameter.

        The `getter` gets called with out parameters:
        ```
        getter()
        ```

        The `setter` is called with the value to set as the only parameter:
        ```
        setter(value)
        ```

        This way functions of the implementing child classes can directly pass
        their member method which is the indented way.
        
        Example
        -------
        ```
        class MyMicroscope(MicroscopeInterface):
            def __init__(self, controller : "Controller") -> None:
                super().__init__(controller)
                
                self.registerMeasurementVariable(
                    MeasurementVariable("tilt", "Tilt", unit="deg"),
                    self._getTilt, self._setTilt
                )

                # ...
            
            def _getTilt(self) -> float:
                return self._microscope_api.getTilt()

            def _setTilt(self, value: float) -> None:
                self._microscope_api.setTilt(value)
        ```    

        Parameters
        ----------
        variable : MeasurementVariable
            The measurement variable object to register
        getter : callable
            The function that is used to get the current value of this 
            `MeasurementVariable` from the microscope, has to return the value
            in the format the `MeasurementVariable` is used to, the first and 
            only parameter is the instance of the microscope
        setter : callable
            The function that is used to set the current value of this 
            `MeasurementVariable` from the microscope, the first parameter is 
            the instance of the microscope, the second is the the value to 
            apply
        """

        self.supported_measurement_variables.append(variable)
        self._measurement_variable_getter_setter_map[variable.unique_id] = (
            getter, setter
        )

    def setInLorentzMode(self, lorentz_mode: bool) -> None:
        """Set whether the microscope should now be in lorentz mode or not.

        This is typically done by switching off the lenses that are close to 
        the speciemen and changing the focus.

        Parameters
        ----------
        lorentz_mode : boolean
            Whether to put the microscope in lorentz mode or not
        """
        raise NotImplementedError()

    def getInLorentzMode(self) -> bool:
        """Get whether the microscope is currently in lorentz mode or not.

        Returns
        -------
        boolean
            Whether the microscope is in lorentz mode or not
        """
        raise NotImplementedError()

    def setMeasurementVariableValue(self, id_: str, value: typing.Union[int, float, str]) -> None:
        """Set the measurement variable defined by its id to the given value.

        A measurement variable is each variable that this microscope can 
        control. The possibilities are defined in the 
        MicroscopeInterface.supported_measurement_variables attribute. The 
        value is the value that the microscope should put the variable to in 
        the measurement variable specific unit.

        Typically this could be the 'focus', the 'magnetic field' (via the 
        objective lense or any lense close to the specimen), the 'tilt' angle
        or anything else. The unit depens on the value to set.

        See Also
        --------
        supported_measurement_variables
        getMeasurementVariableValue()
        MeasurementVariable : The measurement variable class

        Parameters
        ----------
        id_ : str
            The id of the measurement variable
        value : int, float or str
            The value to set in the variable specific type and units
        """

        if not self.supports_parallel_measurement_variable_setting:
            # make sure only this function is currently using the microscope,
            # otherwise two functions may change microscope values at the same time
            # which will mess up things
            self.action_lock.acquire()
        
        if not self.isValidMeasurementVariableValue(id_, value):
            raise ValueError(("Either the id {} does not exist or the value " + 
                              "{} is not valid for the measurement " + 
                              "variable.").format(id_, value))

        elif id_ in self._measurement_variable_getter_setter_map:
            self._measurement_variable_getter_setter_map[id_][1](value)
        else:
            # this cannot happen, if the id doesn't exist the 
            # MicroscopeInterface::isValidMeasurementVariableValue returns 
            # false
            if not self.supports_parallel_measurement_variable_setting:
                self.action_lock.release()
            
            raise ValueError("The id {} does not exist.".format(id_))

        if not self.supports_parallel_measurement_variable_setting:
            # let other functions access the microscope
            self.action_lock.release()

    def getMeasurementVariableValue(self, id_: str) -> typing.Union[int, float, str]:
        """Get the value of the measurement variable defined by its id.

        A measurement variable is each variable that this microscope can 
        control. The possibilities are defined in the 
        MicroscopeInterface.supported_measurement_variables attribute. The 
        current value that this variable has will be returned in the value 
        specific units.

        See Also
        --------
        supported_measurement_variables
        setMeasurementVariableValue()
        MeasurementVariable : The measurement variable class

        Parameters
        ----------
        id_ : str
            The id of the measurement variable

        Returns
        -------
        int, float or str
            The value of the variable in the variable specific type and units
        """

        if not self.supports_parallel_measurement_variable_setting:
            # make sure only this function is currently using the microscope,
            # otherwise two functions may change microscope values at the same time
            # which will mess up things
            self.action_lock.acquire()

        if id_ in self._measurement_variable_getter_setter_map:
            value = self._measurement_variable_getter_setter_map[id_][0]()
        else:
            if not self.supports_parallel_measurement_variable_setting:
                self.action_lock.release()
            
            raise ValueError(("There is no MeasurementVariable for the " + 
                              "id {}.").format(id_))

        if not self.supports_parallel_measurement_variable_setting:
            # let other functions access the microscope
            self.action_lock.release()
        
        return value

    def isValidMeasurementVariableValue(self, id_: str, value: float) -> bool:
        """Get whether the value is allowed for the measurement variable with 
        the id.

        Tells whether the value can safely be set. This is defined by the 
        MeasurementVariables that have a min and a max value. The value is in
        the measurement variable specific units.

        If the id does not exist, Fals will be returned.

        Parameters
        ----------
        id_ : str
            The id of the measurement variable
        value : float
            The value to set in the specific units

        Returns
        -------
        boolean
            Whether the microscope can set the value safely
        """

        for variable in self.supported_measurement_variables:
            if variable.unique_id == id_ and (isinstance(value, (int, float)) and (
                not isinstance(variable.min_value, (int, float)) or 
                value >= variable.min_value) and (
                not isinstance(variable.max_value, (int, float)) or 
                value <= variable.max_value)):
                return True
        
        return False
    
    def getMeasurementVariableById(self, id_: str) -> "MeasurementVariable":
        """Get the measurement variable object by its id.

        Raises
        ------
        KeyError
            When the `id_` does not exist for this microscope
        
        Parameters
        ----------
        id_ : str
            The id of the measurement variable
        
        Returns
        -------
        MeasurementVariable
            The variable object
        """

        f = list(filter(
            lambda v: v.unique_id == id_, 
            self.supported_measurement_variables
        ))

        if len(f) > 0:
            return f[0]
        else:
            raise KeyError(
                "Could not find a measurement variable with id {}.".format(id_)
            )