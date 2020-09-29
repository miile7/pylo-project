import threading

class ExceptionThread(threading.Thread):
    """Represents a Thread that will save exceptions.

    Attributes
    ----------
    exceptions : list of Exception
        A list that contains all the exceptions that were raised while the run 
        method was performed (normally this contains no or exactly one element)
    """

    thread_count = 0

    def __init__(self, *args, **kwargs) -> None:
        """Get the ExceptionThread object."""

        self.exceptions = []
        super(ExceptionThread, self).__init__(*args, **kwargs)
    
    def run(self, *args, **kwargs):
        """Run the thread."""
        print("Starting thread {} (#{}), {} active threads.".format(
            self.name, self.ident, threading.active_count() - 1
        ))
        
        try:
            super(ExceptionThread, self).run(*args, **kwargs)
        except Exception as e:
            self.exceptions.append(e)
        
        if len(self.exceptions) > 0:
            e = ", ".join(["{}: {}".format(type(e), e) for e in self.exceptions])
            e = " with {} exceptions: {}".format(len(self.exceptions), e)
        else:
            e = "."
        
        ExceptionThread.thread_count -= 1
        print("Ending thread {} (#{}), {} active threads{}".format(
            self.name, self.ident, threading.active_count() - 1, e
        ))