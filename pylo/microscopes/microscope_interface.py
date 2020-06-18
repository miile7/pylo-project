class MicroscopeInterface:
    """
    An interface class to communicate with the microscope.

    Attributes
    ----------
    supported_measurement_variables : list of MeasurementVariable
        All the measurement variables that this microscope supports, typically 
        this is the magnetic field (via controlling the lens current of the 
        objective lense or any lense that is close/around the speciemen), the 
        focus and possibly the tilt of the speciemen
    """

    def __init__(self):
        """Get the microscope instance"""
        self.supported_measurement_variables = []

    async def setInLorenzMode(self, lorenz_mode: bool) -> None:
        """Set whether the microscope should now be in lorenz mode or not.

        This is typically done by switching off the lenses that are close to 
        the speciemen and changing the focus.

        Parameters
        ----------
        lorenz_mode : boolean
            Whether to put the microscope in lorenz mode or not
        """
        raise NotImplementedError()

    async def getInLorenzMode(self) -> bool:
        """Get whether the microscope is currently in lorenz mode or not.

        Returns
        -------
        boolean
            Whether the microscope is in lorenz mode or not
        """
        raise NotImplementedError()

    async def setMeasurementVariableValue(self, id_: str, value: float) -> None:
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
        value : float
            The value to set in the specific units
        """
        raise NotImplementedError()

    async def getMeasurementVariableValue(self, id_: str) -> float:
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
        int or float
            The focus current
        """
        raise NotImplementedError()

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
    
    async def resetToSafeState(self) -> None:
        """Set the microscope into its safe state.

        The safe state will be used whenever something bad happens or when the 
        measurement has finished. The microscope will be told to go in the safe 
        state. This should be a state where the microscope can stay for long 
        times until the operator comes again.
        """
        raise NotImplementedError()