import os
import sys
import time
import errno
import types
import random
import typing
import pathlib
import tempfile

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

_debug_mode = True

try:
    import DigitalMicrograph as DM
except (ModuleNotFoundError, ImportError) as e:
    if not _debug_mode:
        raise RuntimeError("This class can onle be used inside the Digital " + 
                        "Micrograph program by Gatan.")
    DM = None

_python_dm_type_map = ({
        "python": int,
        "TagGroup": "Long",
        "dmscript": "number",
        "names": ("long", "integer", "int")
    }, {
        "python": float,
        "TagGroup": "Float",
        "dmscript": "number",
        "names": ("float", "double", "decimal", "realnumber", "number")
    }, {
        "python": bool,
        "TagGroup": "Boolean",
        "dmscript": "number",
        "names": ("bool", "boolean")
    }, {
        "python": str,
        "TagGroup": "String",
        "dmscript": "string",
        "names": ("string", "text")
    }, {
        "python": dict,
        "TagGroup": "TagGroup",
        "dmscript": "TagGroup",
        "names": ("TagGroup", "dict")
    }, {
        "python": list,
        "TagGroup": "TagList",
        "dmscript": "TagGroup",
        "names": ("TagList", "list")
    }
)

def exec_dmscript(*scripts: typing.Union[str, pathlib.PurePath, typing.Tuple[str, typing.Union[str, pathlib.PurePath]]], 
                  readvars: typing.Optional[dict]=None):
    """Execute the `scripts` and prepare the `vars` for getting their values.

    The `scripts` can either be filenames of dm-script files to execute or 
    scripts as strings. The type is guessed automatically. To explicitly set
    the type use a tuple with either 'file' or 'script' at index 0 and the 
    corresponding value at index 1.

    The `readvars` are the variables to read after the script has been executed.
    Those variables have to be defined in the dm-script and they have to be in 
    the global scope, otherwise they will not be readable.

    The `readvars` has to be a dict with the dm-script variable name as the key
    and the variable type as the value. The type can either be a python type or 
    a dm-script type expression. Note that only basic types are supported. 

    `TagGroup` structures can be expressed by a dict. Use the `TagGroup` key as 
    the dict key, the value is the type that is expected at this index. 
    `TagList`s are the same, use a python list and set the types to the indices.
    Both can be replaced with callback functions that will get the path of 
    keys/indices as their only parameter. If a `TagGroup` or `TagList` 
    strucutre is not given, it is auto-guessed. Note that this may have 
    problems because dm-script type definitions in `TagGroup`s are not definite 
    (e.g. float complex and float point are stored in the exact same way and 
    return the same type).

    Supported types:
    - int, aliases: Integer, short, long
    - float, aliases: Float, Double, realnumber, number, decimal
    - boolean
    - string, alias: Text
    - dict, alias: TagGroup
    - list, alias: TagList

    Note that dm-script variabels are case-insensitive. But the python 
    mechanism is not. This means you can use any typing as the key but you can 
    only get the value (on python side) with this exact typing.

    Example
    -------
    >>> prefix = "\n".join((
    ...     "string command = \"select-image\";",
    ...     "number preselected_image = {};".format(show_image)
    ... ))
    >>> vars = {"sel_img_start": "Integer",
    ...         "sel_img_end": int,
    ...         "options": str}
    >>> with exec_dmscript(prefix, path, readvars=vars) as script:
    ...     for i in range(script["sel_img_start"], script["sel_img_end"]):
    ...         do_stuff(i, script["options"])

    Parameters
    ----------
    scripts : str, pathlib.PurePath or tuple
        The file path of the dmscript to execute or the dm-script code or a 
        tuple with 'file' or 'script' at index 0 and the file path or the 
        script code at index 1
    readvars : dict, optional
        The variables to read from the dm-script executed code (after the code
        execution) and to allow getting the value of, the key has to be the 
        name in dm-script, the value is the type, for defining `TagGroup` and 
        `TagList` structures use dicts and tuples or callbacks

    Returns
    -------
    str
        The code to append to the dm-script code
    """
    global _debug_mode

    return DMScriptWrapper(*scripts, readvars=readvars, debug=_debug_mode)

def get_dm_type(datatype: typing.Union[str, type], 
                for_taggroup: typing.Optional[bool]=False):
    """Get the dm-script equivalent for the given `datatype`.

    Note that not all types are supported, even if there is an equvalent in 
    dm-script.

    Raises
    ------
    LookupError
        When the `datatype` is not known

    Parameters
    ----------
    datatype : str or type
        The type to get the dm-script type of, python types and common type 
        expressions are supported
    for_taggroup : boolean, optional
        Whether the datatype should be returned so it can be used directly in 
        `taggroup.GetTagAs<datatype>()` function or not, default: False
    
    Returns
    -------
    str
        The datatype name in dm-script
    """

    global _python_dm_type_map

    if isinstance(datatype, str):
        datatype = datatype.lower()
    
    for type_def in _python_dm_type_map:
        names = list(map(lambda x: x.lower() if isinstance(x, str) else x, 
                         type_def["names"]))
        if datatype in names or datatype == type_def["python"]:
            if for_taggroup:
                return type_def["TagGroup"]
            else:
                return type_def["dmscript"]
    
    raise LookupError("Cannot find the dm-script type for '{}'".format(datatype))

def get_python_type(datatype: typing.Union[str, type]):
    """Get the python equivalent for the given `datatype`.

    Note that not all types are supported, even if there is an equvalent in 
    dm-script.

    Raises
    ------
    LookupError
        When the `datatype` is not known

    Parameters
    ----------
    datatype : str or type
        The type to get the python type of, python types and common type 
        expressions are supported
    
    Returns
    -------
    type
        The datatype name in python
    """

    global _python_dm_type_map

    if isinstance(datatype, str):
        datatype = datatype.lower()
    
    for type_def in _python_dm_type_map:
        names = list(map(lambda x: x.lower() if isinstance(x, str) else x, 
                         type_def["names"]))
        if datatype in names or datatype == type_def["python"]:
            return type_def["python"]
    
    raise LookupError("Cannot find the python type for '{}'".format(datatype))

class DMScriptWrapper:
    """Wraps one or more dm-scripts.
    """

    def __init__(self,
                 *scripts: typing.Union[str, pathlib.PurePath, typing.Tuple[str, typing.Union[str, pathlib.PurePath]]], 
                 readvars: typing.Optional[dict]=None,
                 debug: typing.Optional[bool]=False) -> None:
        """Initialize the script wrapper.

        Parameters
        ----------
        scripts : str, pathlib.PurePath or tuple
            The file path of the dmscript to execute or the dm-script code or a 
            tuple with 'file' or 'script' at index 0 and the file path or the 
            script code at index 1
        readvars : dict, optional
            The variables to read from the dm-script executed code (after the code
            execution) and to allow getting the value of, the key has to be the 
            name in dm-script, the value is the type, for defining `TagGroup` and 
            `TagList` structures use dicts and tuples or callbacks
        debug : bool, optional
            Whether to use the debug mode (allow usage without 
            DigitalMicrograph) or not
        """
        self.scripts = DMScriptWrapper.normalizeScripts(scripts)
        self._creation_time_id = str(round(time.time() * 100))
        self.persistent_tag = "python-dm-communication-" + self._creation_time_id
        self.readvars = readvars
        self.synchronized_readvars = {}
        self.debug = bool(debug)
    
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
        
        dmscript = self.getExecDMScriptCode()
        
        if self.debug:
            with open(tempfile.mkstemp(), "w+") as f:
                f.write(dmscript)
            return True
        else:
            DM.ExecuteScriptString(dmscript)
            self._loadVariablesFromDMScript()
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
        return self.synchronized_readvars.__iter__

    def __len__(self) -> int:
        """Get the number of synchronized variables."""
        return len(self.synchronized_readvars)

    def __contains__(self, var: typing.Any) -> bool:
        """Get whether the `var` is a synchronized dm-script variable."""
        return var in self.synchronized_readvars
    
    def exec(self) -> bool:
        """Execute the code.

        Returns
        -------
        bool
            Success
        """
        return self()
    
    def getExecDMScriptCode(self) -> str:
        """Get the dm-script code to execute.

        The returned code contains all files, all code fragments and 
        the complete synchronizing mechanism.

        Returns
        -------
        str
            The code to execute
        """
        dmscript = [
            "// This code is created automatically by concatenating files and ",
            "// code fragments.",
            "// ",
            "// This code is generated with the exedmscript module."
            "",
            ""
        ]
        
        for kind, script in self.scripts:
            if isinstance(kind, str):
                kind = kind.lower()

            if kind == "file":
                with open(script, "r") as f:
                    dmscript += [
                        "// File {}".format(script),
                        f.read(),
                        ""
                    ]
            elif kind == "script":
                dmscript += [
                    "// Directly given script",
                    script,
                    ""
                ]
        
        dmscript.append(self.getSyncDMCode())
        
        return "\n".join(dmscript)

    def getSyncDMCode(self) -> str:
        """Get the `dm-script` code that has to be added to the executed code 
        for synchronizing.

        Returns
        -------
        str
            The code to append to the dm-script code
        """
        if not isinstance(self.readvars, dict) or len(self.readvars) == 0:
            return ""
        
        # the name of the tag group to use
        sync_code_tg_name = "sync_taggroup_" + self._creation_time_id
        
        # declare and initialize the used variables
        sync_code_prefix = "\n".join((
            "",
            "// Adding synchronizing machanism by using persistent tags.",
            "TagGroup {tg}_user = GetPersistentTagGroup();",
            "number {tg}_index = {tg}_user.TagGroupCreateNewLabeledTag(\"{pt}\");",
            "TagGroup {tg}_tg = NewTagGroup();",
            "{tg}_user.TagGroupSetIndexedTagAsTagGroup({tg}_index, {tg}_tg);",
            ""
        ))
        
        # the template to use for each line
        sync_code_template = "\n".join((
            "// Synchronizing {{val}}",
            "{tg}_index = {tg}_tg.TagGroupCreateNewLabeledTag(\"{{key}}\");",
            "{tg}_tg.TagGroupSetIndexedTagAs{{type}}({tg}_index, {{val}});"
        )).format(tg=sync_code_tg_name, pt=self.persistent_tag)
        
        dmscript = [sync_code_prefix.format(
            tg=sync_code_tg_name, pt=self.persistent_tag
        )]
        
        linearize_functions_added = False

        for var_name, var_type in self.readvars.items():
            if isinstance(var_type, (dict, list, tuple)):
                dmscript += self._recursivelyGetTagGroupDefCode(
                    sync_code_tg_name, var_type, var_name
                )
            else:
                dm_type = get_dm_type(var_type, for_taggroup=True)

                if dm_type == "TagGroup" or dm_type == "TagList":
                    # autoguess a TagGroup/TagList
                    if not linearize_functions_added:
                        dmscript.append(
                            DMScriptWrapper._getLinearizeTagGroupFunctionsCode()
                        )
                    
                    dmscript.append(
                        "__exec_dmscript_linearizeTags({tg}_tg, {key}, \"{key}\");".format(
                            key=var_name, tg=sync_code_tg_name
                    ))
                else:
                    dmscript.append(sync_code_template.format(
                        key=var_name, val=var_name, type=dm_type
                    ))
        
        return "\n".join(dmscript)
    
    def _recursivelyGetTagGroupDefCode(self, dm_tg_name: str, 
                                       type_def: typing.Union[list, dict], 
                                       var_name: str, 
                                       path: typing.Optional[list]=[]) -> list:
        """Get the code for saving a `TagGroup` or `TagList` to the persistent
        tags with a known structure.

        The tagname where the data to synchronize is saved to (direct child of 
        the persistent tags) is the `dm_tg_name` ("_tg" will be appended). 
        
        The `type_def` is either a list or a dict that defines the structure. 
        It can contain more dicts and lists or the name tag name as the key and 
        the datattype as a value (python types and common expressions allowed).

        The `var_name` is the dm-script variable name to synchronize.

        The `path` is for recursive use only. It contains the indices of the 
        parent `TagGroup`/`TagList´/`type_def`-dict. A number (has to be int)
        indicates that this was a `TagList`, a string (also numeric strings 
        supported) indicate that this was a `TagGroup`.

        The executed code will save the `var_name` linearized to the persistent
        tags, each tag name (or index) is separated by "/" (escape: "//"). The 
        type is present for each key called "{{type}}<key name>".

        Raises
        ------
        ValueError
            When the `type_def` neither is a dict nor a list nor a tuple

        Parameters
        ----------
        dm_tg_name : str
            The name of the `TagGroup` to use in the background, this `TagGroup`
            is a direct child of the persistent tags and used for 
            synchronization (this is defined in 
            `DMScriptWrapper::getDMSyncCode()`)
        type_def : dict, list, tuple
            A list or tuple to define datatypes of `TagList`s, a dict to define
            `TagGroup` structures, can contain other dicts, lists or tuples, 
            each value is the datatype, each key is the `TagGroup` key, each
            index is the `TagList` index
        var_name : str
            The dm-script variable name to synchronize
        path : list, optional
            Contains the path to the current value for recursive use, never set 
            this value!
        
        Returns
        -------
        str
            The dm-script code to execute for saving the defined structure to
            the persistent tags
        """
        dmscript = []
        list_mode = False

        if isinstance(type_def, (list, tuple)):
            iterator = enumerate(type_def)
            list_mode = True
        elif isinstance(type_def, dict):
            iterator = type_def.items()
            list_mode = False
        else:
            raise ValueError("The type_def has to be a dict or a list.")

        path = list(path)
        
        for var_key, var_type in iterator:
            if isinstance(var_type, (dict, list, tuple)):
                if list_mode:
                    # important so future calls knwo that this was a list
                    var_key = int(var_key)
                else:
                    var_key = str(var_key)
                dmscript += self._recursivelyGetTagGroupDefCode(
                    dm_tg_name, var_type, var_name, path + [var_key]
                )
            else:
                source_path = ":".join(map(
                    lambda x: "[{}]".format(x) if isinstance(x, int) else x,
                    path + [var_key]
                ))
                destination_path = "/".join(map(
                    lambda x: x.replace("/", "//") if isinstance(x, str) else str(x),
                    [var_name] + path + [var_key]
                ))
                dms = "\n".join((
                    "",
                    "{scripttype} {var}_{varkey}_{t}{r};",
                    "{var}.TagGroupGetTagAs{tgtype}(\"{srcpath}\", {var}_{varkey}_{t}{r});",
                    "{tg}_index = {tg}_tg.TagGroupCreateNewLabeledTag(\"{destpath}\")",
                    "{tg}_tg.TagGroupSetIndexedTagAs{tgtype}({tg}_index, {var}_{varkey}_{t}{r});",
                    "{tg}_index = {tg}_tg.TagGroupCreateNewLabeledTag(\"{{{{type}}}}{destpath}\")",
                    "{tg}_tg.TagGroupSetIndexedTagAsString({tg}_index, \"{tgtype}\");",
                )).format(
                    tg=dm_tg_name, var=var_name, varkey=var_key,
                    scripttype=get_dm_type(var_type, for_taggroup=False),
                    tgtype=get_dm_type(var_type, for_taggroup=True),
                    srcpath=source_path,
                    destpath=destination_path,
                    t=round(time.time() * 100),
                    r=random.randint(0, 99999999)
                )

                dmscript.append(dms)

        return dmscript
    
    def _loadVariablesFromDMScript(self) -> None:
        """Load the variables from the persistent tags to dm-script."""
        
        for var_name, var_type in self.readvars.items():
            # UserTags are enough but they are not supported in python :(
            user_tags = DM.GetPersistentTagGroup()
            path = self.persistent_tag + ":" + var_name
            func_name = "GetTagAs" + get_dm_type(var_type, for_taggroup=True)

            # check if the datatype is supported by trying
            if hasattr(user_tags, func_name):
                func = getattr(user_tags, func_name)
                if callable(func):
                    success, val = func(path)

                    if success:
                        return val
            
            return None

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

        if var_name not in self.synchronized_readvars:
            return None
        else:
            return self.synchronized_readvars[var_name]

    def freeAllSyncedVars(self) -> None:
        """Delete all synchronization from the persistent tags.

        Make sure to always execute this function. Otherwise the persistent 
        tags will be filled with a lot of garbage.
        """
        # python way does not work
        # user_tags = DM.GetPersistentTagGroup()
        # user_tags.TagGroupDeleteTagWithLabel(persistent_tag)

        if not self.debug and DM is not None:
            DM.ExecuteScriptString(
                "GetPersistentTagGroup()." + 
                "TagGroupDeleteTagWithLabel(\"" + self.persistent_tag + "\");"
            )
    
    @staticmethod
    def _getLinearizeTagGroupFunctionsCode():
        """Get the dm code that defines the `__exec_dmscript_linearizeTags()`
        function to save `TagGroup`s and `TagList`s as an 1d-"array"

        Returns
        -------
        str
            The dm script defining the functions
        """

        return """
        string __exec_dmscript_replace(string subject, string search, string replace){
            if(subject.find(search) < 0){
                return subject;
            }

            String r = "";
            number l = search.len();
            number pos;
            while((pos = subject.find(search)) >= 0){
                r.stringAppend(subject.left(pos) + replace);
                subject = subject.right(subject.len() - pos - l);
            }

            return r;
        }

        void __exec_dmscript_linearizeTags(TagGroup &linearized, TagGroup tg, string path){
            for(number i = 0; i < tg.TagGroupCountTags(); i++){
                String label;
                if(tg.TagGroupIsList()){
                    label = i + "";
                }
                else{
                    label = tg.TagGroupGetTagLabel(i).__exec_dmscript_replace("/", "//");
                }
                number type = tg.TagGroupGetTagType(i, 0);
                string type_name = "";
                number index;
                string p = path + "/" + label;

                if(type == 0){
                    // TagGroup
                    TagGroup value;
                    
                    tg.TagGroupGetIndexedTagAsTagGroup(i, value);
                    __exec_dmscript_linearizeTags(linearized, value, p);
                    
                    if(value.TagGroupIsList()){
                        type_name = "TagList";
                    }
                    else{
                        type_name = "TagGroup";
                    }
                }
                else if(type == 2){
                    // tag is a short
                    number value

                    tg.TagGroupGetIndexedTagAsShort(i, value)
                    index = linearized.TagGroupCreateNewLabeledTag(p);
                    linearized.TagGroupSetIndexedTagAsShort(index, value);
                    type_name = "Short";
                }
                else if(type == 3){
                    // tag is a long
                    number value

                    tg.TagGroupGetIndexedTagAsLong(i, value)
                    index = linearized.TagGroupCreateNewLabeledTag(p);
                    linearized.TagGroupSetIndexedTagAsLong(index, value);
                    type_name = "Long";
                }
                else if(type == 4){
                    number value;
                    
                    tg.TagGroupGetIndexedTagAsUInt16(index, value);
                    index = linearized.TagGroupCreateNewLabeledTag(p);
                    linearized.TagGroupSetIndexedTagAsUInt16(index, value);
                    type_name = "UInt16";
                }
                else if(type == 5){
                    number value;
                    
                    tg.TagGroupGetIndexedTagAsUInt32(index, value);
                    index = linearized.TagGroupCreateNewLabeledTag(p);
                    linearized.TagGroupSetIndexedTagAsUInt32(index, value);
                    type_name = "UInt32";
                }
                else if(type == 6){
                    // tag is a float
                    number value

                    tg.TagGroupGetIndexedTagAsFloat(i, value)
                    index = linearized.TagGroupCreateNewLabeledTag(p);
                    linearized.TagGroupSetIndexedTagAsFloat(index, value);
                    type_name = "Float";
                }
                else if(type == 7){
                    // tag is a double
                    number value

                    tg.TagGroupGetIndexedTagAsDouble(i, value)
                    index = linearized.TagGroupCreateNewLabeledTag(p);
                    linearized.TagGroupSetIndexedTagAsDouble(index, value);
                    type_name = "Double";
                }
                else if(type == 7){
                    // tag is a boolean
                    number value

                    tg.TagGroupGetIndexedTagAsBoolean(i, value)
                    index = linearized.TagGroupCreateNewLabeledTag(p);
                    linearized.TagGroupSetIndexedTagAsBoolean(index, value);
                    type_name = "Boolean";
                }
                // skip type=15, this is more complicated types like rgbnumber, 
                // shortpoint, longpoint, floatcomplex, doublecomplex, and
                // shortrect, longrect and float rect
                else if(type == 20){
                    // tag is a string
                    string value

                    tg.TagGroupGetIndexedTagAsString(i, value)
                    index = linearized.TagGroupCreateNewLabeledTag(p);
                    linearized.TagGroupSetIndexedTagAsString(index, value);
                    type_name = "String";
                }
                
                if(type_name != ""){
                    index = linearized.TagGroupCreateNewLabeledTag("{{type}}" + p);
                    linearized.TagGroupSetIndexedTagAsString(index, type_name);
                }
            }
        }
        """

    @staticmethod
    def normalizeScripts(scripts: typing.Sequence) -> typing.List[tuple]:
        """Create a tuple for each script in the `scripts` with index 0 telling
        if it is a file or script and index 1 telling the corresponding value.

        Parameters
        ----------
        scripts : list or tuple of string, pathlib.PurePath or tuple
            The scripts
        
        Returns
        -------
        list of tuple
            A list containing a tuple in each entry, each tuple contains 'file'
            or 'script' at index 0 and the path or the script at index 1
        """

        normalized = []

        for script in scripts:
            if isinstance(script, (list, tuple)) and len(script) >= 2:
                normalized.append(script)
            elif isinstance(script, pathlib.PurePath):
                normalized.append(("file", script))
            elif isinstance(script, str) and script != "":
                if _is_pathname_valid(script):
                    normalized.append(("file", script))
                else:
                    normalized.append(("script", script))

        return normalized

# Sadly, Python fails to provide the following magic number for us.
ERROR_INVALID_NAME = 123
'''
Windows-specific error code indicating an invalid pathname.

See Also
----------
https://docs.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-
    Official listing of all such codes.
'''

def _is_pathname_valid(pathname: str) -> bool:
    '''
    `True` if the passed pathname is a valid pathname for the current OS;
    `False` otherwise.

    Taken from https://stackoverflow.com/a/34102855/5934316
    '''
    # If this pathname is either not a string or is but is empty, this pathname
    # is invalid.
    try:
        if not isinstance(pathname, str) or not pathname:
            return False

        # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
        # if any. Since Windows prohibits path components from containing `:`
        # characters, failing to strip this `:`-suffixed prefix would
        # erroneously invalidate all valid absolute Windows pathnames.
        _, pathname = os.path.splitdrive(pathname)

        # Directory guaranteed to exist. If the current OS is Windows, this is
        # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
        # environment variable); else, the typical root directory.
        root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
            if sys.platform == 'win32' else os.path.sep
        assert os.path.isdir(root_dirname)   # ...Murphy and her ironclad Law

        # Append a path separator to this directory if needed.
        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep

        # Test whether each path component split from this pathname is valid or
        # not, ignoring non-existent and non-readable path components.
        for pathname_part in pathname.split(os.path.sep):
            try:
                os.lstat(root_dirname + pathname_part)
            # If an OS-specific exception is raised, its error code
            # indicates whether this pathname is valid or not. Unless this
            # is the case, this exception implies an ignorable kernel or
            # filesystem complaint (e.g., path not found or inaccessible).
            #
            # Only the following exceptions indicate invalid pathnames:
            #
            # * Instances of the Windows-specific "WindowsError" class
            #   defining the "winerror" attribute whose value is
            #   "ERROR_INVALID_NAME". Under Windows, "winerror" is more
            #   fine-grained and hence useful than the generic "errno"
            #   attribute. When a too-long pathname is passed, for example,
            #   "errno" is "ENOENT" (i.e., no such file or directory) rather
            #   than "ENAMETOOLONG" (i.e., file name too long).
            # * Instances of the cross-platform "OSError" class defining the
            #   generic "errno" attribute whose value is either:
            #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
            #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
            except OSError as exc:
                if hasattr(exc, 'winerror'):
                    if exc.winerror == ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    # If a "TypeError" exception was raised, it almost certainly has the
    # error message "embedded NUL character" indicating an invalid pathname.
    except TypeError as exc:
        return False
    # If no exception was raised, all path components and hence this
    # pathname itself are valid. (Praise be to the curmudgeonly python.)
    else:
        return True
    # If any other exception was raised, this is an unrelated fatal issue
    # (e.g., a bug). Permit this exception to unwind the call stack.
    #
    # Did we mention this should be shipped with Python already?