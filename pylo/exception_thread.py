import logging
import threading

from .logginglib import do_log
from .logginglib import log_error
from .logginglib import log_debug
from .logginglib import get_logger
from .stop_program import StopProgram

class ExceptionThread(threading.Thread):
    """Represents a Thread that will save exceptions.

    Attributes
    ----------
    exceptions : list of Exception
        A list that contains all the exceptions that were raised while the run 
        method was performed (normally this contains no or exactly one element)
    """

    def __init__(self, *args, **kwargs) -> None:
        """Get the ExceptionThread object."""

        self.exceptions = []
        self._logger = get_logger(self)
        
        super(ExceptionThread, self).__init__(*args, **kwargs)
    
    def run(self, *args, **kwargs):
        """Run the thread."""
        
        if do_log(self._logger, logging.INFO):
            self._logger.info(("Starting thread '{}' (#{}), currently {} " + 
                               "active threads").format(self.name, self.ident, 
                               threading.active_count()))
        
        log_debug(self._logger, ("Starting thread '{}' with args '{}' and " + 
                                 "kwargs '{}'").format(self.name, args, kwargs))
        
        try:
            super(ExceptionThread, self).run(*args, **kwargs)
        except Exception as e:
            if (isinstance(e, TypeError) and hasattr(self, "_target") and 
                not callable(self._target)):
                err = TypeError("A type error was raised and the 'target' is " + 
                                "not callable. Probably that is the cause.")
                log_error(self._logger, err)
                raise err from e
                
            if isinstance(e, StopProgram):
                log_debug(self._logger, "Stopping program", exc_info=e)
            else:
                log_error(self._logger, e)
            self.exceptions.append(e)
        
        if (len(self.exceptions) == 1 and 
            isinstance(self.exceptions[0], StopProgram)):
            e = ", thread wants to end the program (StopProgram raised)"
        elif len(self.exceptions) > 0:
            e = ", ".join(["{}: {}".format(type(e), e) for e in self.exceptions])
            e = " with {} exceptions: {}".format(len(self.exceptions), e)
        else:
            e = "."
        
        if do_log(self._logger, logging.INFO):
            self._logger.info(("Ending thread '{}' (#{}), currently {} " + 
                               "active threads{}").format(self.name, self.ident, 
                               threading.active_count() - 1, e))