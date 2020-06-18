from .blocked_function_error import BlockedFunctionError

class BlockedFunction:
    """This class represents a object method which is currently not executable.

    This is used for protecting machines in emergency case.

    Attributes
    ----------
    func : callable
        The function that originally should be executed
    func_name : str
        The name of the method
    """

    def __init__(self, func: callable, func_name: str):
        """Create a blocked function object.

        Parameters
        ----------
        func : callable
            The function that originally should be executed
        func_name : str
            The name of the method
        """

        self.func = func
        self.func_name = func_name
    
    def __call__(self, *args, **kwargs):
        """Allow calling this, this will always raise an error.

        The object method is replaced with this object so it. To allow calling
        the functions, this object is callable

        Raises
        ------
        BlockedFunctionError
            Always
        """

        raise BlockedFunctionError(
            "The function {} is currently blocked.".format(self.func_name)
        )