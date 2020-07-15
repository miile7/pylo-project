import threading

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
        super(ExceptionThread, self).__init__(*args, **kwargs)
    
    def run(self, *args, **kwargs):
        """Run the thread."""
        try:
            super(ExceptionThread, self).run(*args, **kwargs)
        except Exception as e:
            self.exceptions.append(e)