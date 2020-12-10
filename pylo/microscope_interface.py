import typing
import logging
import threading

from .device import Device
from .logginglib import do_log
from .datatype import Datatype
from .logginglib import log_error
from .logginglib import get_logger
from .vulnerable_machine import VulnerableMachine
class MicroscopeInterface(Device, VulnerableMachine):
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

    def __init__(self, controller : "Controller", name: typing.Optional[str]=None, 
                 config_group_name: typing.Optional[str]=None, 
                 config_defaults: typing.Optional[dict]={}, 
                 description: typing.Optional[str]="") -> None:
        """Get the microscope instance.

        Parameters
        ----------
        controller : Controller
            The controller
        name : str
            The name to show in the GUI and to use to load this device
        config_group_name : str
            The group name this device should use to save persistent values in the 
            configuration
        config_defaults : dict
            The default values that this device has which can be used internally,
            optiona, default: {}
        description : str
            A description for this device, currently not used, default: ""
        """
        super(MicroscopeInterface, self).__init__(kind="microscope", 
            name=name, config_group_name=config_group_name,
            config_defaults=config_defaults, description=description)
        self._logger = get_logger(self)
        
        self.supported_measurement_variables = []
        self.supports_parallel_measurement_variable_setting = False
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

        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Registering measurement variable '{}'".format(
                variable.unique_id))

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

        Raises
        ------
        KeyError
            When the `id_` does not exist
        ValueError
            When the `value` is not allowed for this variable

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
            The value to set in the variable specific type and units, this will
            be parsed automatically if the measurement variable has a `format`
        """

        if not self.supports_parallel_measurement_variable_setting:
            # make sure only this function is currently using the microscope,
            # otherwise two functions may change microscope values at the same time
            # which will mess up things
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Locking microscope")
            
            self.action_lock.acquire()
        
        var = self.getMeasurementVariableById(id_)

        if not self.isValidMeasurementVariableValue(id_, value):
            err = ValueError(("The value '{}' is not valid for the " + 
                              "measurement variable '{}'.").format(value, id_))
            log_error(self._logger, err)
            raise err

        elif id_ in self._measurement_variable_getter_setter_map:
            if isinstance(var.format, (type, Datatype)):
                value = var.format(value)
            
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Setting '{}' to '{}'".format(id_, value))
            
            self._measurement_variable_getter_setter_map[id_][1](value)
        else:
            # this cannot happen, if the id doesn't exist the 
            # MicroscopeInterface::isValidMeasurementVariableValue returns 
            # false
            if not self.supports_parallel_measurement_variable_setting:
                if do_log(self._logger, logging.DEBUG):
                    self._logger.debug("Releasing microscope lock")
                self.action_lock.release()
            
            err = ValueError("The id {} does not exist.".format(id_))
            log_error(self._logger, err)
            raise err

        if not self.supports_parallel_measurement_variable_setting:
            # let other functions access the microscope
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Releasing microscope lock")
            
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
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Locking microscope")

            self.action_lock.acquire()

        if id_ in self._measurement_variable_getter_setter_map:
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Asking for value of '{}'".format(id_))
            
            value = self._measurement_variable_getter_setter_map[id_][0]()
            
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Received value '{}' for '{}'".format(value, id_))
        else:
            if not self.supports_parallel_measurement_variable_setting:
                if do_log(self._logger, logging.DEBUG):
                    self._logger.debug("Releasing microscope lock")
                self.action_lock.release()
            
            err = ValueError(("There is no MeasurementVariable for the " + 
                              "id {}.").format(id_))
            log_error(self._logger, err)
            raise err

        if not self.supports_parallel_measurement_variable_setting:
            # let other functions access the microscope
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Releasing microscope lock")
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
            if variable.unique_id == id_:
                if isinstance(variable.format, (type, Datatype)):
                    try:
                        value = variable.format(value)
                    except ValueError:
                        # could not be converted
                        return False
                    
                if isinstance(value, (int, float)):
                    if (isinstance(variable.min_value, (int, float)) and 
                        value < variable.min_value):
                        return False

                    if (isinstance(variable.max_value, (int, float)) and 
                        value > variable.max_value):
                        return False
                
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