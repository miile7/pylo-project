import DigitalMicrograph as DM
import time

required_files = {}

def executeDMScript(filename, synchronized_variables={}):
    """Require the given `filename` and execute the contained script as a 
    dm-script.

    The `synchronized_variables` can later be received via the 
    `getDMScriptVariable()` function.

    Example
    -------
    >>> with executeDmScript(<name>, <vars>) as script:
    ...     # ...
    ...     var = script.getSyncedVar(<var>)

    Parameters
    ----------
    sync_vars : dict
        The variables to synchronize, the key is the exact name of the variable 
        in the dm-script code, the value is the datatype that is used for the 
        `TagGroupSetTagAs<datatype>()`, `TagGroupGetTagAs<datatype>()`, ... 
        functions

    Returns
    -------
    str
        The code to append to the dm-script code
    """
    global required_files

    script = DMScriptWrapper(filename, synchronized_variables)
    required_files[filename] = script
    
    return script

def getDMScriptVariable(filename, variable_name):
    """Get the variable of the of the executed file at the `filename`.

    Raises
    ------
    KeyError
        When the `filename` was not required by the `executeDMScript()` 
        function

    Parameters
    ----------
    variable_name : str
        The name of the variable in the dm-script, has to be registered in 
        the `executeDMScript()` function
    
    Returns
    -------
    mixed
        The variable value or None if it does not exist
    """
    global required_files

    script = required_files[filename]
    return script.getSyncedVar(variable_name)

class DMScriptWrapper:
    """Wraps a dm-script.

    Parameters
    ----------
    filename : str
        The file name of the file to require
    persistent_tag : str
        The unique persistent tag name where the variables will be saved
    synchronized_variables : dict
        The variables to synchronize, the key is the exact name of the variable 
        in the dm-script code, the value is the datatype that is used for the 
        `TagGroupSetTagAs<datatype>()`, `TagGroupGetTagAs<datatype>()`, ... 
        functions
    """

    def __init__(self, filename: str, syncronized_variables: dict) -> None:
        """Initialize the script wrapper."""
        self.filename = filename
        self._creation_time_id = str(round(time.time() * 100))
        self.persistent_tag = "python-dm-communication-" + self._creation_time_id
        self.syncronized_variables = syncronized_variables
    
    def __del__(self):
        self.freeAllSyncedVars()
    
    def __call__(self) -> bool:
        """Execute the code.

        Returns
        -------
        bool
            Success
        """
        with open(self.filename) as f:
            script = f.read()
        
            script += "\n" + self.getSyncDMCode()

            DM.ExecuteScriptString(script)
            return True
            
        return False
    
    def __enter__(self):
        self.exec()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.freeAllSyncedVars()
    
    def exec(self) -> bool:
        """Execute the code.

        Returns
        -------
        bool
            Success
        """
        return self()

    def getSyncDMCode(self):
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
        
        dm_script = sync_code_prefix.format(
            tg=sync_code_tg_name, pt=self.persistent_tag
        )
        
        for var_name, var_type in self.syncronized_variables.items():
            dm_script += sync_code_template.format(
                tg=sync_code_tg_name, pt=self.persistent_tag, var=var_name, 
                type=var_type[0].upper() + var_type[1:].lower()
            )
        
        return dm_script

    def getSyncedVar(self, var_name):
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
        if var_name not in self.syncronized_variables:
            return None
        
        var_type = self.syncronized_variables[var_name]

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

    def freeAllSyncedVars(self):
        """Delete all synchronization from the persistent tags.

        Make sure to always execute this function. Otherwise the persistent 
        tags will be filled with a lot of garbage.
        """
        # python way does not work
        # user_tags = DM.GetPersistentTagGroup()
        # user_tags.TagGroupDeleteTagWithLabel(persistent_tag)

        DM.ExecuteScriptString(
            "GetPersistentTagGroup()." + 
            "TagGroupDeleteTagWithLabel(\"" + self.persistent_tag + "\");"
        )