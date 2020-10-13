try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

class ExecutionOutsideEnvironmentError(ModuleNotFoundError):
    """An error indicating that a module is missing that is essential to build 
    the execution environment. Most of the times this is because the program 
    is executed outside its normal environment."""
    pass