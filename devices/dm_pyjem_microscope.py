import os
import json
import typing
import logging
import subprocess

from pylo import loader
from pylo import Datatype
from pylo import pylolib
from pylo import logginglib
from pylo.logginglib import log_debug


# python <3.6 does not define a ModuleNotFoundError, use this fallback
from pylo.errors import FallbackModuleNotFoundError
from pylo.errors import ExecutionOutsideEnvironmentError

try:
    import DigitalMicrograph as DM
except (FallbackModuleNotFoundError, ImportError) as e:
    raise ExecutionOutsideEnvironmentError("Could not load module execdmscript.")

DMMicroscope = loader.getDeviceClass("Digital Micrograph Microscope")

class DMPyJEMMicroscope(DMMicroscope):
    def __init__(self, *args, **kwargs) -> None:
        """Get the microscope instance"""
        self.initialized = False
        super().__init__(*args, **kwargs)

        self.pyjem_olcurrent_path = None
        self.python_35_path = None
        self.pyjem_olcurrent_args = ["--output", "json"]
        self.initialized = True

    def _ensureExecutablePaths(self, raise_error: typing.Optional[bool]=True) -> None:
        """Ensure that the `DMPyJEMMicroscope.pyjem_olcurrent_path` is set.

        Parameters
        ----------
        raise_error : bool
            Whether to raise an error if the path does not exist or not
        """

        if self.pyjem_olcurrent_path is None:
            self.pyjem_olcurrent_path = self.controller.configuration.getValue(
                self.config_group_name, "pyjem_olcurrent-path", 
                default_value=None)
            
            try:
                if not os.path.isfile(self.pyjem_olcurrent_path):
                    raise FileNotFoundError()
            except (TypeError, OSError) as e:
                if self.pyjem_olcurrent_path is None:
                    msg = ("The 'pyjem_olcurrent.py' path is not set. Set " +
                           "it in the configuration first.")
                else:
                    msg = ("The 'pyjem_olcurrent.py' at the path '{}' does " + 
                           "not exist or is not valid.").format(self.python_35_path)
                
                err = FileNotFoundError(msg)

                if raise_error:
                    pylolib.log_error(self._logger, err)
                    raise err from e
                else:
                    self.pyjem_olcurrent_path = None

        if self.python_35_path is None:
            self.python_35_path = self.controller.configuration.getValue(
                self.config_group_name, "python-35-path", 
                default_value=None)
            
            try:
                if not os.path.isfile(self.python_35_path):
                    raise FileNotFoundError()
            except (TypeError, OSError) as e:
                if self.python_35_path is None:
                    msg = ("The python 3.5 executable path is not set. Set " +
                           "it in the configuration first.")
                else:
                    msg = ("The python 3.5 executable at the path '{}' does " + 
                           "not exist or is not valid.").format(self.python_35_path)
                
                err = FileNotFoundError(msg)

                if raise_error:
                    pylolib.log_error(self._logger, err)
                    raise err from e
                else:
                    self.python_35_path = None
    
    def _execute(self, set_fine: typing.Optional[typing.Union[int, float]]=False,
                 set_coarse: typing.Optional[typing.Union[int, float]]=False,
                 get_fine: typing.Optional[bool]=False,
                 get_coarse: typing.Optional[bool]=False,
                 raise_error: typing.Optional[bool]=True):
        """Get and/or set the objective fine and coarse lens value by executing
        the 'pyjem_olcurrent.py' program.

        Parameters
        ----------
        set_fine, set_coarse : int, float or False
            The value to set the fine or coarse value to or False to not set it
        get_fine, get_coarse : bool
            Whether to return the fine or coarse value or not
        raise_error : bool
            Whether to raise a errors or to return None instead
        
        Returns
        -------
        int or None, int or None
            The fine and the coarse value or none if `get_fine` or `get_coarse`
            is False
        """

        self._ensureExecutablePaths(raise_error)

        if ((self.pyjem_olcurrent_path is None or self.python_35_path is None) and
            not raise_error):
            return None, None

        try:
            command = [self.python_35_path, 
                       self.pyjem_olcurrent_path]
            
            operation = []
            if isinstance(set_coarse, (int, float)) and type(set_coarse) != bool:
                command += ["--setc", str(set_coarse)]
                operation.append("set the coarse value '{}'".format(set_coarse))

            if isinstance(set_fine, (int, float)) and type(set_fine) != bool:
                command += ["--setf", str(set_fine)]
                operation.append("set the fine value '{}'".format(set_fine))

            if get_coarse:
                command += ["--getc"]
                operation.append("get the coarse value")

            if get_fine:
                command += ["--getf"]
                operation.append("get the fine value")
            
            command += self.pyjem_olcurrent_args
            
            if len(operation) == 0:
                log_debug(self._logger, ("Skipping execution of " + 
                                         "'pyjem_olcurrent.py' because there " + 
                                         "is nothing to do."))
                return None, None
            
            log_debug(self._logger, ("Trying to {} by executing the " + 
                                     "command '{}'.").format(
                                        pylolib.human_concat_list(operation, 
                                                                  surround="", 
                                                                  word=" and "),
                                        command))
            
            s, gms_venv_python = DM.GetPersistentTagGroup().GetTagAsString("Private:Python:Python Path")

            if not s:
                raise KeyError("The python installation of GMS cannot be found.")
            
            python_dir = os.path.dirname(self.python_35_path)

            my_env = os.environ.copy()             
            my_env["PYTHONHOME"] = python_dir
            my_env["PYTHONPATH"] = "{};".format(python_dir)
            my_env["PATH"] = my_env["PATH"].replace(gms_venv_python, python_dir)
                
            result = subprocess.run(command, stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE, env=my_env)

            log_debug(self._logger, ("Command was executed and returned " + 
                                     "'{}'").format(result.stdout.decode('utf-8')))
        except OSError as e:
            err = OSError("Could not execute the command for setting the " + 
                          "objective lens current due to an error: {}".format(e))
            pylolib.log_error(self._logger, err)

            if not raise_error:
                return None, None
            else:
                raise err from e
        
        response = result.stdout.decode('utf-8').strip()
        if not response.startswith("{") and "{" in response:
            response = response[response.index("{"):]
        if not response.endswith("}") and "}" in response:
            response = response[:response.rindex("}")+1]

        try:
            response = json.loads(response)
        except json.decoder.JSONDecodeError as e:
            err = IOError("Could not read the response of the " + 
                          "'pyjem_olcurrent.py' program")
            pylolib.log_error(self._logger, err)

            if not raise_error:
                return None, None
            else:
                raise err from e
        
        if "error" in response:
            err = OSError(("The 'pyjem_olcurrent.py' program returned an " + 
                           "error: {}").format(response["error"]))
            pylolib.log_error(self._logger, err)

            if not raise_error:
                return None, None
            else:
                raise err
        
        try:
            if ("output" not in response or 
                (get_fine and "getf" not in response["output"]) or
                (get_coarse and "getc" not in response["output"])):
                raise IOError()
        except (TypeError, IOError) as e:
            err = IOError(("The 'pyjem_olcurrent.py' program returned " + 
                        "uncomplete data."))
            pylolib.log_error(self._logger, err)

            if not raise_error:
                return None, None
            else:
                raise err from e
        
        return (response["output"]["getf"] if get_fine else None,
                response["output"]["getc"] if get_coarse else None)
    
    def _setObjectiveLensCurrent(self, value: float) -> None:
        """Set the objective lense current.

        The value corresponds to I/O output value without carry.

        Raises
        ------
        OSError
            When the program could not be executed
        IOError
            When the response of the program is not readable
        
        Parameters
        ----------
        value : int or float
            The value to set the objective lense current to in objective fine
            lense steps
        """
        fine_value, coarse_value = self._splitObjectiveLensCurrent(value)

        self._execute(set_fine=fine_value, set_coarse=coarse_value, 
                      raise_error=self.initialized)
        
        if self.initialized:
            self._ol_currents = {"fine": fine_value, "coarse": coarse_value}

        self._waitForVariableValue("ol-current", self._getObjectiveLensCurrent, 
                                   value)
    
    def _getObjectiveLensCurrent(self) -> float:
        """Get the objective lense current in the current units.

        Returns
        -------
        float
            The actual current of the objective lense at the microscope,
            measured in objective fine lense steps
        """

        fine_value, coarse_value = self._execute(get_fine=True, get_coarse=True, 
                                                 raise_error=self.initialized)
        if fine_value is None:
            fine_value = 0
        if coarse_value is None:
            coarse_value = 0
        
        self._ol_currents = {"fine": fine_value, "coarse": coarse_value}

        return self._joinObjectiveLensCurrent(fine_value, coarse_value)
    
    @staticmethod
    def defineConfigurationOptions(configuration: "AbstractConfiguration", 
                                   config_group_name: typing.Optional[str]="pyjem-microscope",
                                   config_defaults: typing.Optional[dict]={}, 
                                   *args, **kwargs) -> None:
        """Define which configuration options this class requires.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration to define the required options in
        config_group_name : str, optional
            The group name this device should use to save persistent values in
            the configuration, this is given automatically when loading this
            object as a device, default: "pyjem-microscope"
        config_defaults : dict, optional
            The default values to use, this is given automatically when loading
            this object as a device, default: {}
        """
        DMMicroscope.defineConfigurationOptions(configuration, 
                                                config_group_name, 
                                                config_defaults, *args, 
                                                **kwargs)
        
        # add the option for the pyjem_olcurrent.py path
        configuration.addConfigurationOption(
            config_group_name, 
            "pyjem_olcurrent-path", 
            datatype=Datatype.filepath.withbase(os.path.dirname(__file__)), 
            description=("The path where the `pyjem_olcurrent.py` lays. Note " + 
                         "that PyJEM supports only python 3.5.6.\n\n" + 
                         "To use this, install miniconda or anaconda. Read " + 
                         "details in the help of the 'python-35-path' setting."), 
            ask_if_not_present=True
        )
        if "pyjem_olcurrent-path" in config_defaults:
            configuration.addConfigurationOption(config_group_name, 
                                                 "pyjem_olcurrent-path",
                                                 default_value=config_defaults["pyjem_olcurrent-path"])
        
        # add the option for the pyjem_olcurrent.py path
        configuration.addConfigurationOption(
            config_group_name, 
            "python-35-path", 
            datatype=Datatype.filepath.withbase(os.path.dirname(__file__)), 
            description=("The absolute path where the python 3.5 executable " + 
                         "lays. Note that PyJEM supports only python 3.5.6.\n\n" + 
                         "To use this, install miniconda or anaconda " + 
                         "(miniconda comes with GMS, so it is not needed if " + 
                         "you see this message in DigitalMicrograph). Then " + 
                         "create a new environment " + 
                         "(e.g. `conda create --name pyjem-legacy python=3.5`)." + 
                         "Add the path of the python executable of this " + 
                         "environment here. \n\n" + 
                         "The executable can be found by typing " + 
                         "`conda activate pyjem-legacy`. Then use " + 
                         "`where python` on windows and `which python` on " + 
                         "linux and macOS. Type the path in here."), 
            ask_if_not_present=True
        )

        if "python-35-path" in config_defaults:
            configuration.addConfigurationOption(config_group_name, 
                                                 "python-35-path",
                                                 default_value=config_defaults["python-35-path"])

