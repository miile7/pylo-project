import typing

class MeasurementVariable:
    """A physical variable that can be changed.

    This class represents variables that can be changed and observed by the 
    microscope. Typically this is the focus, the magnetic field (via the 
    objective lense), the tilt of the specimen ect.

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
    """

    def __init__(self, unique_id: str, name: str, 
                 min_value: typing.Optional[float]=None, 
                 max_value: typing.Optional[float]=None, 
                 unit: typing.Optional[str]=None):
        """Create a MeasurementVariable.

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
            The unit this measurement variable is expressed in, None for no unit
        """
        self.unique_id = unique_id
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit