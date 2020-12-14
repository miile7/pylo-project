import os
import csv
import time
import queue
import typing
import logging
import pathlib

from .logginglib import log_debug
from .logginglib import log_error
from .logginglib import get_logger
from .pylolib import path_like
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

    def __init__(self, log_path: typing.Union[path_like]) -> None:
        """Get the ExceptionThread object.
        
        Parameters
        ----------
        log_path : str, pathlib.PurePath
            The path to write to
        queue : Queue
            The queue to process lines in the log
        """

        logger = get_logger(self)

        self.queue = queue.Queue()
        self.log_path = log_path
        self.running = False
        self._finish = False

        log_dir = os.path.dirname(self.log_path)
        if not os.path.exists(log_dir):
            log_debug(logger, ("Directory '{}' does not exist, creating " + 
                      "it").format(log_dir))
            os.makedirs(log_dir, 0o660, exist_ok=True)
        
        super().__init__(name="log")
        self._logger = logger

    def run(self):
        """Run the thread.

        This will execute a loop which can be terminated by the 
        `LogThread::stop()` function. The loop will check the internal queue,
        if there is data, the data will be written to the log file.
        """

        self.running = True
        self._finish = False

        log_debug(self._logger, "Starting log thread")
        
        while self.running:
            if not self.queue.empty():
                if not self._writeQueueToLog():
                    break
            
            time.sleep(0.01)
    
    def _writeQueueToLog(self) -> None:
        """Write the current queue to the log file."""

        log_debug(self._logger, "Queue is not empty, writing to log")
        log_debug(self._logger, "Opening file '{}'".format(self.log_path))
        
        # open file
        try:
            log_file = open(self.log_path, "a", newline="")
        except OSError as error:
            self.running = False
            log_error(self._logger, error)
            raise error
            
        # initialize writer
        log_writer = csv.writer(
            log_file, delimiter=",", quotechar="\"", 
            quoting=csv.QUOTE_MINIMAL
        )
        
        log_debug(self._logger, "Writing '{}' elements until queue is empty".format(
                               self.queue.qsize()))
        
        # write all new rows
        while not self.queue.empty():
            cells = self.queue.get()
            log_writer.writerow(cells)
        
        log_debug(self._logger, "Done with writing, queue is now empty")
        log_debug(self._logger, "Closing file '{}'".format(self.log_path))
        
        # close the files
        log_file.close()
        
        return True
        
    def finishAndStop(self) -> None:
        """Finish the current queue and then stop the execution."""
        log_debug(self._logger, "Writing all elements from queue and then stopping")
        self._writeQueueToLog()
        self.stop()
    
    def stop(self) -> None:
        """Stop the thread loop."""
        log_debug(self._logger, "Stopping")
        self.running = False

    def addToLog(self, cells: typing.Sequence) -> None:
        """Add the cells to the log.

        Parameters
        ----------
        cells : list
            The list of cells to add to the current row of the log
        """
        log_debug(self._logger, "Adding row '{}' to log".format(cells))
        self.queue.put(cells)