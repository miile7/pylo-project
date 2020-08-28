import os
import re
import sys
import time
import errno
import types
import random
import typing
import pathlib

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

try:
    import DigitalMicrograph as DM
except (ModuleNotFoundError, ImportError) as e:
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
                  readvars: typing.Optional[dict]=None,
                  debug: typing.Optional[bool]=False):
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

    return DMScriptWrapper(*scripts, readvars=readvars, debug=debug)

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
        self._slash_split_reg = re.compile("(?<!/)/(?!/)")
    
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
            path = os.path.join(os.path.dirname(__file__), "tmp-execdmscript.s")
            with open(path, "w+") as f:
                f.write(dmscript)
                f.close()
                print(("execdmscript: Did not execute script but saved to {} " + 
                      "because file is running in debug mode.").format(path))
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

                if (dm_type in ("TagGroup", "TagList") or 
                    var_type in (dict, list, tuple)):
                    # autoguess a TagGroup/TagList
                    if not linearize_functions_added:
                        linearize_functions_added = True
                        dmscript.append(
                            DMScriptWrapper._getLinearizeTagGroupFunctionsCode()
                        )
                    
                    dmscript.append(
                        "__exec_dmscript_linearizeTags({tg}_tg, {key}, \"{key}\", \"{key}\");".format(
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

        dmscript.append("\n".join((
            "if(!{tg}_tg.TagGroupDoesTagExist(\"{{{{available-paths}}}}{var}\")){{",
                "number index_{var}_{t}{r} = {tg}_tg.TagGroupCreateNewLabeledTag(\"{{{{available-paths}}}}{var}\");",
                "{tg}_tg.TagGroupSetIndexedTagAsString(index_{var}_{t}{r}, \"\");",
            "}}"
        )).format(tg=dm_tg_name, var=var_name, t=round(time.time() * 100),
                  r=random.randint(0, 99999999)))
        
        for var_key, var_type in iterator:
            dms = ""
            if isinstance(var_type, (dict, list, tuple)):
                if list_mode:
                    # important so future calls knwo that this was a list
                    var_key = int(var_key)
                else:
                    var_key = str(var_key)
                
                dmscript += self._recursivelyGetTagGroupDefCode(
                    dm_tg_name, var_type, var_name, path + [var_key]
                )

                if isinstance(var_type, dict):
                    var_type = "TagGroup"
                else:
                    var_type = "TagList"
            else:
                dms = "\n".join((
                    "{scripttype} {var}_{varkey}_{t}{r};",
                    "{var}.TagGroupGetTagAs{tgtype}(\"{srcpath}\", {var}_{varkey}_{t}{r});",
                    "{tg}_index = {tg}_tg.TagGroupCreateNewLabeledTag(\"{destpath}\")",
                    "{tg}_tg.TagGroupSetIndexedTagAs{tgtype}({tg}_index, {var}_{varkey}_{t}{r});",
                ))

            source_path = ":".join(map(
                lambda x: "[{}]".format(x) if isinstance(x, int) else x,
                path + [var_key]
            ))
            destination_path = "/".join(map(
                lambda x: x.replace("/", "//") if isinstance(x, str) else str(x),
                [var_name] + path + [var_key]
            ))
            dms = "\n".join((
                dms,
                "{tg}_index = {tg}_tg.TagGroupCreateNewLabeledTag(\"{{{{type}}}}{destpath}\")",
                "{tg}_tg.TagGroupSetIndexedTagAsString({tg}_index, \"{tgtype}\");",
                "string available_index_{var}_{varkey}_{t}{r};",
                "{tg}_tg.TagGroupGetTagAsString(\"{{{{available-paths}}}}{var}\", available_index_{var}_{varkey}_{t}{r});",
                "available_index_{var}_{varkey}_{t}{r} += \"{destpath};\";",
                "{tg}_tg.TagGroupSetTagAsString(\"{{{{available-paths}}}}{var}\", available_index_{var}_{varkey}_{t}{r});",
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

        self.synchronized_readvars = {}
        
        for var_name, var_type in self.readvars.items():
            path = self.persistent_tag + ":" + var_name
            
            var_type = self.readvars[var_name]
            if isinstance(var_type, str):
                dm_type = get_dm_type(var_type, for_taggroup=True)
            else:
                dm_type = None
            
            if (dm_type in ("TagGroup", "TagList") or 
                isinstance(var_type, (dict, list, tuple)) or
                var_type in (dict, list, tuple)):
                value = None

                # get the paths of all elements added to this group, recursive
                # travelling is not possible because TagGroups cannot be saved
                # to variables
                success, tg_keys = (DM.GetPersistentTagGroup().
                                    GetTagAsString(
                                        self.persistent_tag + ":{{available-paths}}" + str(var_name)
                                    ))

                if success:
                    tg_keys = tg_keys.split(";")

                    for tg_key in tg_keys:
                        paths = self._slash_split_reg.split(tg_key)
                        
                        for i, path in enumerate(paths):
                            # build the value structure
                            if i == 0:
                                # set the variables values as the "base"
                                if (dm_type == "TagGroup" or 
                                    isinstance(var_type, dict) or
                                    var_type == dict):
                                    cur_type = "TagGroup"
                                    if value is None:
                                        value = {}
                                    value_ref = value
                                else:
                                    cur_type = "TagList"
                                    if value is None:
                                        value = []
                                    value_ref = value
                            else:
                                # parse the key depending on the parent
                                # type, cur_type is not overwritten yet
                                if cur_type == "TagList":
                                    key = int(path)
                                    while key >= len(value_ref):
                                        # also prepare the current index 
                                        # with none so it can be set by 
                                        # value_ref[key] = v, if the 
                                        # key already exists and is None
                                        # append was wrong
                                        value_ref.append(None)
                                elif cur_type == "TagGroup":
                                    key = path
                                    if key not in value_ref:
                                        value_ref[key] = None
                                else:
                                    break
                                
                                # the the current path that the persistent
                                # TagGroup contains the key of
                                cur_path = "/".join(map(str, paths[0:(i + 1)]))
                                
                                # get the current datatype
                                s, cur_type = (DM.GetPersistentTagGroup().
                                        GetTagAsString(
                                            self.persistent_tag + 
                                            ":{{type}}" + str(cur_path)
                                        ))
                            
                                if cur_type == "TagGroup":
                                    # create a new dict and save it in 
                                    # the current key, then set the
                                    # reference to this new dict
                                    if isinstance(value_ref[key], dict):
                                        value_ref[key] = {}
                                    value_ref = value_ref[key]
                                elif cur_type == "TagList":
                                    # create a new list, add as many times
                                    # None as necessary to reach the
                                    # current index
                                    if not isinstance(value_ref[key], list):
                                        value_ref[key] = []
                                    value_ref = value_ref[key]
                                else:
                                    # the current type is a real value, 
                                    # get the parsed value and stop (there 
                                    # should not be any more paths coming,
                                    # just to be sure)
                                    s, v = self._getParsedValueFromPersistentTags(
                                        "{}:{}".format(
                                            self.persistent_tag, cur_path
                                        ), 
                                        cur_type
                                    )

                                    if s:
                                        value_ref[key] = v
                                    else:
                                        success = False
                                    break
            else:
                success, value = self._getParsedValueFromPersistentTags(
                    path, var_type
                )
            
            if success:
                self.synchronized_readvars[var_name] = value

    def _getParsedValueFromPersistentTags(self, path, var_type):
        dm_type = get_dm_type(var_type, for_taggroup=True)
        # UserTags are enough but they are not supported in python :(
        # do not save the persistent tags to a variable, this way they do 
        # not work anymore (for any reason)
        if dm_type == "Long":
            success, value = DM.GetPersistentTagGroup().GetTagAsLong(path)
        elif dm_type == "Float":
            success, value = DM.GetPersistentTagGroup().GetTagAsFloat(path)
        elif dm_type == "Boolean":
            success, value = DM.GetPersistentTagGroup().GetTagAsBoolean(path)
        elif dm_type == "String":
            success, value = DM.GetPersistentTagGroup().GetTagAsString(path)
        else:
            raise ValueError("The datatype '{}' is not supported".format(var_type))
        
        return success, value

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

        void __exec_dmscript_linearizeTags(TagGroup &linearized, TagGroup tg, string var_name, string path){
            string available_paths = "";
            if(linearized.TagGroupDoesTagExist("{{available-paths}}" + var_name)){
                linearized.TagGroupGetTagAsString("{{available-paths}}" + var_name, available_paths);
            }

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
                    __exec_dmscript_linearizeTags(linearized, value, var_name, p);
                    
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

                    available_paths += p + ";";
                }
            }
            
            if(!linearized.TagGroupDoesTagExist("{{available-paths}}" + var_name)){
                number ind = linearized.TagGroupCreateNewLabeledTag("{{available-paths}}" + var_name);
                linearized.TagGroupSetIndexedTagAsString(ind, available_paths);
            }
            else{
                linearized.TagGroupSetTagAsString("{{available-paths}}" + var_name, available_paths);
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
                if os.path.isfile(script):
                    normalized.append(("file", script))
                else:
                    normalized.append(("script", script))

        return normalized