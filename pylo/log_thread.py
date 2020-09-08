import os
import csv
import time
import queue
import typing
import pathlib

from .exception_thread import ExceptionThread

class LogThread(ExceptionThread):
    """This class is used by the `Measurement` to asynchronously write the log 
    to the file.

    This thread will open the log file as soon as there is new data, then write
    the data and close the file again. This is a log of I/O-operations but the 
    measurement is slow anyway and if there is more data at once, this class 
    will write all pooled data.

    Opening and closing the file every time is trying to make the loss of data
    as small as possible if the program crashes.

    Attributes
    ----------
    log_path : str, pathlib.PurePath
        The path to write to
    """

    def __init__(self, log_path: typing.Union[str, pathlib.PurePath]) -> None:
        """Get the ExceptionThread object.
        
        Parameters
        ----------
        log_path : str, pathlib.PurePath
            The path to write to
        queue : Queue
            The queue to process lines in the log
        """

        self.queue = queue.Queue()
        self.log_path = log_path
        self.running = False
        self._finish = False

        log_dir = os.path.dirname(self.log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, 0o660)
        
        super().__init__()

    def run(self):
        """Run the thread.

        This will execute a loop which can be terminated by the 
        `LogThread::stop()` function. The loop will check the internal queue,
        if there is data, the data will be written to the log file.
        """

        self.running = True
        self._finish = False
        
        while self.running:
            if not self.queue.empty():
                if not self._writeQueueToLog():
                    break
            
            time.sleep(0.01)
    
    def _writeQueueToLog(self):
        """Write the current queue to the log file."""

        # open file
        try:
            log_file = open(self.log_path, "a", newline="")
        except OSError as error:
            self.exceptions.append(error)
            self.running = False
            return False
            
        # initialize writer
        log_writer = csv.writer(
            log_file, delimiter=",", quotechar="\"", 
            quoting=csv.QUOTE_MINIMAL
        )
        
        # write all new rows
        while not self.queue.empty():
            cells = self.queue.get()
            log_writer.writerow(cells)
        
        # close the files
        log_file.close()
        
        return True
        
    def finishAndStop(self):
        """Finish the current queue and then stop the execution."""
        self._writeQueueToLog()
        self.stop()
    
    def stop(self):
        """Stop the thread loop."""
        self.running = False

    def addToLog(self, cells):
        """Add the cells to the log.

        Parameters
        ----------
        cells : list
            The list of cells to add to the current row of the log
        """
        self.queue.put(cells)