import io
import csv
import typing
import logging
import datetime
import traceback

class InvertedFilter(logging.Filter):
    """Allow all records except those with the given `name`."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def filter(self, record):
        if record.name != self.name:
            return 1
        else:
            return 0

class CsvFormatter(logging.Formatter):
    """Format the log output as a csv."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.output = io.StringIO()
        self.writer = csv.writer(self.output, quoting=csv.QUOTE_ALL)
        self.cols = {"name": lambda r: r.name,
                     "funcName": lambda r: r.funcName, 
                     "levelname": lambda r: r.levelname, 
                     "message": lambda r: r.getMessage(), 
                     "threadName": lambda r: r.threadName, 
                     "filename": lambda r: r.filename, 
                     "lineno": lambda r: r.lineno, 
                     "asctime": lambda r: datetime.datetime.utcfromtimestamp(r.created).strftime('%Y-%m-%d %H:%M:%S'), 
                     "pathname": lambda r: r.pathname, 
                     "exc_info": lambda r: ("{} '{}': {}".format(r.exc_info[0],
                                            r.exc_info[1], 
                                            traceback.format_tb(r.exc_info[2])) 
                                            if isinstance(r.exc_info, tuple)
                                            else r.exc_info),
                     "exc_text": lambda r: r.exc_text, 
                     "stack_info": lambda r: r.stack_info}
        self.writer.writerow(self.cols.keys())

    def format(self, record: logging.LogRecord) -> str:
        self.writer.writerow([self.formatCell(f(record)) for f in self.cols.values()])
        data = self.output.getvalue()
        self.output.truncate(0)
        self.output.seek(0)
        return data.strip()
    
    def formatCell(self, cell: typing.Any) -> str:
        return str(cell).replace("\n", "\\n").replace("\r", "\\r")

def record_factory(name, level, fn, lno, msg, args, exc_info, func=None, 
                   extra=None, sinfo=None) -> logging.LogRecord:
    frames = traceback.extract_stack(limit=6)
    frame = frames[0]
    return logging.LogRecord(name, level, frame.filename, frame.lineno,
                             msg, args, exc_info, frame.name, sinfo)
    

__do_log_cache = {}
def do_log(logger: logging.Logger, log_level: int) -> bool:
    """Whether to log the `log_level` to the given `logger` or not.
    
    Parameters
    ----------
    logger : logging.Logger
        The logger object
    log_level : int
        The log level to check

    Returns
    -------
    bool
        Whther to do the log or not
    """
    global __do_log_cache

    if logger.name not in __do_log_cache:
        __do_log_cache[logger.name] = {}
    
    if log_level not in __do_log_cache[logger.name]:
        from .config import ENABLED_PROGRAM_LOG_LEVELS
        __do_log_cache[logger.name][log_level] = (logger.isEnabledFor(log_level) and 
                                                  log_level in ENABLED_PROGRAM_LOG_LEVELS)
    return __do_log_cache[logger.name][log_level]

def clear_do_log_cache() -> None:
    """Clear the `do_log()` cache."""
    global __do_log_cache
    __do_log_cache = {}

def log_error(logger: logging.Logger, error: Exception, 
              logging_level: typing.Optional[int]=logging.ERROR) -> None:
    """Log the given exception if the error level is allowed to log for this 
    logger.
    
    Parameters
    ----------
    logger : logging.Logger
        The logger object
    error : Exception
        The exception to log
    loggin_level : int, optional
        The level to log for, default: logging.ERROR
    """
    if do_log(logger, logging_level):
        logger.log(logging_level, 
                   "{}: {}".format(error.__class__.__name__, error), 
                   exc_info=error)

def log_debug(logger: logging.Logger, msg: str, *args,
              logging_level: typing.Optional[int]=logging.DEBUG, **kwargs) -> None:
    """Log the given `msg` to the `logger` if logging is enabled.

    All `args` and `kwargs` will be passed to the `logger` instance. 

    Logging can be disabled on either the logging module or in the `pylo.config`.
    The result defines whether to log or not. This result is cached to prevent
    walking through logger hierarchies or to import the config module over and
    over again.

    Changing logging on runtime is not supported.
    
    Parameters
    ----------
    logger : logging.Logger
        The logger object
    msg : str
        The message to log
    loggin_level : int, optional
        The level to log for, default: logging.DEBUG
    """
    if do_log(logger, logging_level):
        logger.log(logging_level, msg, *args, **kwargs)

def get_logger(obj: typing.Union[str, object], 
               create_msg: typing.Optional[bool]=True, 
               instance_args: typing.Optional[typing.Sequence]=None,
               instance_kwargs: typing.Optional[typing.Mapping]=None) -> logging.Logger:
    """Get the logger for the given object.
    
    Parameters
    ----------
    obj : object or str
        The object that requests the logger or a string how to call the logger
    create_msg : bool, optional
        Whether to write a message to the log that the `obj` is now created,
        default: True
    instance_args : sequence
        The arguments that were used to create the instance
    instance_kwargs : sequence
        The keyword arguments that were used to create the instance
    
    Returns
    -------
    logging.Logger
        The logger object
    """
    if isinstance(obj, str):
        classname = obj
    else:
        classname = obj.__class__.__name__
    logger = logging.getLogger("pylo.{}".format(classname))
    
    if create_msg and do_log(logger, logging.DEBUG):
        if instance_args is not None:
            instance_args = " with args '{}'".format(instance_args)
        else:
            instance_args = ""

        if instance_kwargs is not None:
            instance_kwargs = " {} kwargs '{}'".format(
                                    "and" if instance_args != "" else "with", 
                                    instance_kwargs)
        else:
            instance_kwargs = ""

        logger.debug("Creating new instance of {}{}{}".format(classname,
                     instance_args, instance_kwargs))
    return logger

def create_handlers() -> typing.Sequence[logging.Handler]:
    """Create the logging handlers to write debug information into the debug 
    file and the info logs into the output stream.

    Use:
    ```python
    >>> logger = logging.getLogger('pylo')
    >>> logger.setLevel(logging.DEBUG)

    >>> # add the handlers to the logger
    >>> for handler in create_handlers():
    ...     logger.addHandler(handler)
    ```

    Returns
    -------
    sequence of handlers
        The handlers to add to the logger
    """

    # create file handler which logs even debug messages
    from .config import PROGRAM_LOG_FILE
    dfm = CsvFormatter()
    fh = logging.FileHandler(PROGRAM_LOG_FILE, mode="a+", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(dfm)

    # exclude from loggings
    fh.addFilter(InvertedFilter("pylo.Datatype"))
    fh.addFilter(InvertedFilter("pylo.OptionsDatatype"))

    # create console handler with a higher log level
    ifm = logging.Formatter('%(message)s (#%(lineno)d@%(name)s)')
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(ifm)

    from .config import ENABLED_PROGRAM_LOG_LEVELS
    if logging.DEBUG in ENABLED_PROGRAM_LOG_LEVELS:
        print("Logging debug information to {}".format(PROGRAM_LOG_FILE))

    return fh, ch