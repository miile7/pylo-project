import logging

from .errors import BlockedFunctionError

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

    def __init__(self, func: callable, func_name: str) -> None:
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
        self._logger = logging.Logger("pylo.BlockedFunction")
        if self._logger.isEnabledFor(logging.DEBUG):
            self._log_debug = True
        else:
            self._log_debug = False
        if self._log_debug:
            self._logger.debug("Blocking function '{}'".format(func_name))
    
    def __call__(self, *args, **kwargs) -> None:
        """Allow calling this, this will always raise an error.

        The object method is replaced with this object so it. To allow calling
        the functions, this object is callable

        Raises
        ------
        BlockedFunctionError
            Always
        """

        if self._log_debug:
            self._logger.debug("Blocked function '{}' is called".format(self.func_name),
                            stack_info=True)
        raise BlockedFunctionError(
            "The function {} is currently blocked.".format(self.func_name)
        )