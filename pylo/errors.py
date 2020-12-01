try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass
FallbackModuleNotFoundError = ModuleNotFoundError

class ExecutionOutsideEnvironmentError(ModuleNotFoundError):
    """An error indicating that a module is missing that is essential to build 
    the execution environment. Most of the times this is because the program 
    is executed outside its normal environment."""
    pass

class BlockedFunctionError(LookupError):
    """An error indicating that the called function must not be called because
    it is blocked.
    """
    pass

class DeviceImportError(ImportError):
    """An error indicating that a `Device` file could not be imported."""
    pass

class DeviceClassNotDefined(AttributeError):
    """An error indicating that a `Device` file was found but the class name 
    does not exist in this file or is not a class."""
    pass

class DeviceCreationError(RuntimeError):
    """An error indicating that the `Device` file and class are found but when 
    creating the instance an error occurred."""
    pass