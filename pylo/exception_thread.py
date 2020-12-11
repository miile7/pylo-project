import logging
import threading

from .logginglib import do_log
from .logginglib import log_error
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
        self._logger.info(("Starting thread '{}' (#{}), currently {} active " + 
                           "threads").format(self.name, self.ident, 
                           threading.active_count() - 1))
        
        try:
            super(ExceptionThread, self).run(*args, **kwargs)
        except Exception as e:
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
        
        self._logger.info(("Ending thread '{}' (#{}), currently {} active " + 
                           "threads{}").format(self.name, self.ident, 
                           threading.active_count() - 1, e))