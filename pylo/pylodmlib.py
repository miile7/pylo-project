import os
import time
import types
import typing

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

try:
    import DigitalMicrograph as DM
    outside_mode = False
except (ModuleNotFoundError, ImportError) as e:
    raise RuntimeError("This class can onle be used inside Digital Micrograph.")
    # outside_mode = True

def executeDMScript(file_path: str, 
                    synchronized_variables: typing.Optional[dict]={}, 
                    require_before: typing.Optional[typing.List[str]]=[],
                    script_prefix: typing.Optional[str]=""):
    """Require the given `file_path` and execute the contained script as a 
    dm-script.

    The `synchronized_variables` can later be received via the 
    `getDMScriptVariable()` function.

    Example
    -------
    >>> with executeDmScript(<name>, <vars>) as script:
    ...     # ...
    ...     var = script.getSyncedVar(<var>)
    ...     var2 = script["var2"]

    Parameters
    ----------
    file_path : str
        The file path of the file to require
    synchronized_variables : dict, optional
        The variables to synchronize, the key is the exact name of the 
        variable in the dm-script code, the value is the datatype that is 
        used for the `TagGroupSetTagAs<datatype>()`, 
        `TagGroupGetTagAs<datatype>()`, ...
    require_before : list of strings, optional
        File paths of dm-script files to require before requiring the `file`
    script_prefix : str, optional
        Script to prefix before the `file_path`

    Returns
    -------
    str
        The code to append to the dm-script code
    """

    return DMScriptWrapper(file_path, synchronized_variables, require_before,
                           script_prefix)

class DMScriptWrapper:
    """Wraps a dm-script.

    Parameters
    ----------
    file_path : str
        The file path of the file to require
    persistent_tag : str
        The unique persistent tag name where the variables will be saved
    synchronized_variables : dict
        The variables to synchronize, the key is the exact name of the variable 
        in the dm-script code, the value is the datatype that is used for the 
        `TagGroupSetTagAs<datatype>()`, `TagGroupGetTagAs<datatype>()`, ... 
        functions
    require_before : list
        A list of file paths to require before requiring the `file_path`
    script_prefix : str, optional
        Script to prefix before the `file_path`
    """

    def __init__(self, file_path: str, 
                 synchronized_variables: typing.Optional[dict]={}, 
                 require_before: typing.Optional[typing.List[str]]=[],
                 script_prefix: typing.Optional[str]="") -> None:
        """Initialize the script wrapper.
        
        Parameters
        ----------
        file_path : str
            The file path of the file to require
        synchronized_variables : dict, optional
            The variables to synchronize, the key is the exact name of the 
            variable in the dm-script code, the value is the datatype that is 
            used for the `TagGroupSetTagAs<datatype>()`, 
            `TagGroupGetTagAs<datatype>()`, ...
        require_before : list of strings, optional
            File paths of dm-script files to require before requiring the `file`
        script_prefix : str, optional
            Script to prefix before the `file_path`
        """
        self.file_path = file_path
        self._creation_time_id = str(round(time.time() * 100))
        self.persistent_tag = "python-dm-communication-" + self._creation_time_id
        self.synchronized_variables = synchronized_variables
        self.require_before = require_before
        self.script_prefix = script_prefix
    
    def __del__(self) -> None:
        """Desctruct the object."""
        self.freeAllSyncedVars()
    
    def __call__(self) -> bool:
        """Execute the code.

        Returns
        -------
        bool
            Success
        """
        global outside_mode

        prefix = []
        if isinstance(self.require_before, (list, tuple)):
            for fp in self.require_before:
                with open(fp, "r") as f:
                    prefix.append(f.read())
        
        with open(self.file_path, "r") as f:
            script = "\n\n".join(prefix) + "\n\n"
            script += self.script_prefix + "\n\n"
            script += f.read()
        
            script += "\n" + self.getSyncDMCode()

            if outside_mode:
                print(script)
                path = os.path.join(os.path.dirname(__file__), "pylodmlib-tmp-script.s")
                f = open(path, "w+")
                f.write(script)
                f.close()
                
            else:
                DM.ExecuteScriptString(script)
            
            return True
            
        return False
    
    def __enter__(self) -> "DMScriptWrapper":
        """Enter the `with`-block."""
        self.exec()

        return self
    
    def __exit__(self, exc_type: typing.Optional[typing.Type[BaseException]],
                 exc_instance: typing.Optional[BaseException],
                 exc_traceback: typing.Optional[types.TracebackType]) -> bool:
        """Exit the `with`-block."""
        self.freeAllSyncedVars()

    def __getitem__(self, var: typing.Any) -> typing.Any:
        """Get the dm script variable with the `var`."""
        return self.getSyncedVar(var)

    def __iter__(self) -> typing.Iterator:
        """Get the iterator to iterate over the dm-script variables."""
        return self.synchronized_variables.__iter__

    def __len__(self) -> int:
        """Get the number of synchronized variables."""
        return len(self.synchronized_variables)

    def __contains__(self, var: typing.Any) -> bool:
        """Get whether the `var` is a synchronized dm-script variable."""
        return var in self.synchronized_variables
    
    def exec(self) -> bool:
        """Execute the code.

        Returns
        -------
        bool
            Success
        """
        return self()

    def getSyncDMCode(self) -> str:
        """Get the `dm-script` code that has to be added to the executed code 
        for synchronizing.

        Returns
        -------
        str
            The code to append to the dm-script code
        """
        # the name of the tag group to use
        sync_code_tg_name = "sync_taggroup_" + self._creation_time_id
        
        # declare and initialize the used variables
        sync_code_prefix = "\n".join((
            "// synchronizing variables via the user persistent tags",
            "TagGroup {tg}_user = GetPersistentTagGroup();",
            "number {tg}_index = {tg}_user.TagGroupCreateNewLabeledTag(\"{pt}\");",
            "TagGroup {tg}_tg = NewTagGroup();",
            "{tg}_user.TagGroupSetIndexedTagAsTagGroup({tg}_index, {tg}_tg);"
        )) + "\n"
        
        # the template to use for each line
        sync_code_template = "\n".join((
            "{tg}_index = {tg}_tg.TagGroupCreateNewLabeledTag(\"{var}\");",
            "{tg}_tg.TagGroupSetIndexedTagAs{type}({tg}_index, {var});"
        ))
        
        dm_script = [sync_code_prefix.format(
            tg=sync_code_tg_name, pt=self.persistent_tag
        )]
        
        for var_name, var_type in self.synchronized_variables.items():
            dm_script.append(sync_code_template.format(
                tg=sync_code_tg_name, pt=self.persistent_tag, var=var_name, 
                type=var_type[0].upper() + var_type[1:].lower()
            ))
        
        return "\n" + "\n".join(dm_script)

    def getSyncedVar(self, var_name: str) -> typing.Any:
        """Get the value of the `var_name` dm-script variable.

        If the `var_name` is synchronized via the `getSyncDMCode()` function, 
        the value of the variabel can be received by this function.

        Parameters
        ----------
        var_name : str
            The name of the variable in the dm-script code

        Returns
        -------
        mixed
            The variable value
        """
        global outside_mode

        if var_name not in self.synchronized_variables or outside_mode:
            return None
        
        var_type = self.synchronized_variables[var_name]

        # UserTags are enough but they are not supported in python :(
        user_tags = DM.GetPersistentTagGroup()
        path = self.persistent_tag + ":" + var_name
        func_name = "GetTagAs" + var_type[0].upper() + var_type[1:].lower()

        # check if the datatype is supported by trying
        if hasattr(user_tags, func_name):
            func = getattr(user_tags, func_name)
            if callable(func):
                success, val = func(path)

                if success:
                    return val
        
        return None

    def freeAllSyncedVars(self) -> None:
        """Delete all synchronization from the persistent tags.

        Make sure to always execute this function. Otherwise the persistent 
        tags will be filled with a lot of garbage.
        """
        # python way does not work
        # user_tags = DM.GetPersistentTagGroup()
        # user_tags.TagGroupDeleteTagWithLabel(persistent_tag)
        global outside_mode

        if not outside_mode:
            DM.ExecuteScriptString(
                "GetPersistentTagGroup()." + 
                "TagGroupDeleteTagWithLabel(\"" + self.persistent_tag + "\");"
            )