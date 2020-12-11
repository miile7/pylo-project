import os
import sys
import time
import typing
import logging
import textwrap
import threading
import traceback

# python <3.6 does not define a ModuleNotFoundError, use this fallback
from .errors import FallbackModuleNotFoundError
from .errors import ExecutionOutsideEnvironmentError

try:
    import DigitalMicrograph as DM
except (FallbackModuleNotFoundError, ImportError) as e:
    DM = None

from .datatype import Datatype
from .datatype import OptionDatatype
from .stop_program import StopProgram
from .abstract_view import AskInput
from .abstract_view import AbstractView
from .abstract_configuration import AbstractConfiguration

from .logginglib import do_log
from .logginglib import log_error
from .logginglib import get_logger
from .pylolib import parse_value
from .pylolib import get_datatype_name

if DM is not None:
    # for development only, execdmscript is another module that is developed
    # separately
    try:
        import dev_constants
        load_from_dev = True
    except (FallbackModuleNotFoundError, ImportError) as e:
        load_from_dev = False

    if load_from_dev:
        if hasattr(dev_constants, "execdmscript_path"):
            if not dev_constants.execdmscript_path in sys.path:
                sys.path.insert(0, dev_constants.execdmscript_path)
            
    import execdmscript
else:
    raise ExecutionOutsideEnvironmentError("Could not load module execdmscript.")

class DMView(AbstractView):
    def __init__(self) -> None:
        """Get the view object."""
        if DM == None:
            raise RuntimeError("This class can only be used inside the " + 
                               "Digital Micrograph program by Gatan.")
            
        super().__init__()

        # the name to use for the current progress dialog in the persistent tags
        self._progress_dialog_progress_tagname = None
        # the name to use for the current text in the persistent tags
        self._progress_dialog_text_tagname = None
        # the name to use for the dialogs success
        self._progress_dialog_success_tagname = None
        # the name to use for killing the progress dialog
        self._progress_dialog_kill_tagname = None
        # 1 if the user pressed ok, 0 if the user cancelled, -1 if the dialog 
        # is told to kill itself from outside, None if the result is unknown
        self._progress_dialog_success = None
        # the path where all the dm_view_*.s files are in
        self._rel_path = os.path.dirname(__file__)
        # the text that is created vai the print function
        self._out = ""
        # the maximum numbers of characters in one line
        self.line_length = 100
        # all tagnames that have been set by this object at any time
        self._created_tagnames = set()

        # whether to execute the all dm-scripts with debug=True or not, this is
        # a shorthand for debugging and prevents reloading the view (and 
        # therefore restarting the program) for debugging every time
        self._exec_debug = False

        self._logger = get_logger(self)

    def showHint(self, hint : str) -> None:
        """Show the user a hint.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        hint : str
            The text to show
        """
        dmscript = "showAlert(msg, 2);"
        setvars = {"msg": hint}
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug(("Showing alert by executing dmscript '{}' " + 
                                "with setvars '{}'").format(dmscript, setvars))
        with execdmscript.exec_dmscript(dmscript, setvars=setvars, 
                                        debug=self._exec_debug):
            pass

    def showError(self, error : typing.Union[str, Exception], how_to_fix: typing.Optional[str]=None) -> None:
        """Show the user a hint.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        hint : str
            The text to show
        how_to_fix : str, optional
            A text that helps the user to interpret and avoid this error,
            default: None
        """
        msg = ""
        if isinstance(error, Exception):
            try:
                msg = type(error).__name__
            except:
                pass
        
        if msg == "":
            msg = "Error"
            
        msg += ": " + str(error)

        print(msg)
        print("  Fix:", how_to_fix)

        self.print(msg)
        self.print("  Fix:", how_to_fix)

        if isinstance(error, Exception):
            traceback.print_exc()
            log_error(self._logger, error)
        elif do_log(self._logger, logging.ERROR):
            self._logger.error(msg)

        if isinstance(how_to_fix, str) and how_to_fix != "":
            msg += "\n\nPossible Fix:\n{}".format(how_to_fix)

        dmscript = "showAlert(msg, 0);"
        setvars = setvars={"msg": msg}
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Executing dmscript '{}' with setvars '{}'".format(
                               dmscript, setvars))
        with execdmscript.exec_dmscript(dmscript, setvars=setvars, 
                                        debug=self._exec_debug):
            pass

    def askForDecision(self, text: str, options: typing.Optional[typing.Sequence[str]]=("Ok", "Cancel")) -> int:
        """Ask for a decision between the given `options`.

        The `options` are shown to the user depending on the view 
        implementation. In most of the times this are the buttons shown on a 
        dialog.

        The selected index will be returned.

        Raises
        ------
        ValueError
            When the `options` is empty
        StopProgram
            When the view is closed in another way (e.g. the close icon of a 
            dialog is clicked)
        
        Parameters
        ----------
        text : str
            A text that is shown to the users to explain what they are deciding
        options : sequence of str
            The texts to show to the users they can select from
        
        Returns
        -------
        int
            The selected index
        """

        if len(options) == 0:
            raise ValueError("The options must not be empty.")
        elif len(options) == 2:
            dmscript = "number index = TwoButtonDialog(text, button0, button1);"
            readvars = {
                "index": int
            }
            setvars = {
                "text": text,
                "button0": options[0],
                "button1": options[1]
            }
        
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug(("Asking for decision by executing " + 
                                    "dmscript '{}' with setvars '{}' and " + 
                                    "readvars '{}'").format(dmscript, setvars,
                                    readvars))
            with execdmscript.exec_dmscript(dmscript, setvars=setvars, 
                                            readvars=readvars, 
                                            debug=self._exec_debug) as script:
                index = script["index"]

                # for dm-script the buttons are the "confirm" and the "cancel"
                # buttons, so the left button (button0 in this case) is always
                # true, the right button (button1 in this case) is always false
                # which are, converted to int, 0 and 1 in the exact other way
                # than this function is retunring its values
                if index == 0:
                    index = 1
                elif index == 1:
                    index = 0
        else:
            id_ = "__pylo_pressed_button_{}".format(int(time.time() * 100))
            setvars = {
                "text": text,
                "persistent_tag_name": id_,
                "title": "Please select"
            }
            self._created_tagnames.add(id_)

            dmscript_button_pressed_handlers = []
            dmscript_button_creations = []

            for i, o in enumerate(options):
                setvars["button{}".format(i)] = o
                dmscript_button_pressed_handlers.append(
                    ("void button{i}_pressed(object self){{" + 
                        "self.button_pressed({i});" + 
                    "}}").format(i=i))
                dmscript_button_creations.append(
                    ("b = DLGCreatePushButton(button{i}, \"button{i}_pressed\");" + 
                     "b.DLGWidth(80);" + 
                     "wrapper.DLGAddElement(b);").format(i=i))

            dmscript = "\n".join([
                "class ButtonDialog : UIFrame{",
                    "void button_pressed(object self, number i){",
                        "if(GetPersistentTagGroup().TagGroupDoesTagExist(persistent_tag_name)){",
                            "GetPersistentTagGroup().TagGroupDeleteTagWithLabel(persistent_tag_name);",
                        "}",
                        "GetPersistentTagGroup().TagGroupCreateNewLabeledTag(persistent_tag_name);",
                        "GetPersistentTagGroup().TagGroupSetTagAsShort(persistent_tag_name, i);",
                        "self.close();",
                        "exit(0);",
                    "}",
                    ""] + 
                    dmscript_button_pressed_handlers + 
                    [""
                    "object init(object self){",
                        "TagGroup dlg, dlg_items, wrapper, label, b;",
                        "dlg = DLGCreateDialog(title, dlg_items);",
                        "",
                        "dlg_items.DLGAddElement(DLGCreateLabel(text));",
                        "",
                        "wrapper = DLGCreateGroup();",
                        "wrapper.DLGTableLayout({}, 1, 1);".format(len(options)),
                        "dlg_items.DLGAddElement(wrapper);",
                        ""] + 
                        dmscript_button_creations + 
                        ["",
                        "self.super.init(dlg);",
                        "return self;",
                    "}",
                "}",
                "alloc(ButtonDialog).init().display(title);"
            ])

            if do_log(self._logger, logging.DEBUG):
                self._logger.debug(("Asking for decision by executing " + 
                                    "dmscript '{}' with setvars '{}' and " + 
                                    "readvars '{}'").format(dmscript, setvars,
                                    readvars))
                self._logger.debug("Deleting persistent tag with label '{}'".format(
                                    id_))
            DM.GetPersistentTagGroup().DeleteTagWithLabel(id_)
            with execdmscript.exec_dmscript(dmscript, setvars=setvars, 
                                            debug=self._exec_debug):
                # wait for dm-script to show the dialog, the user takes longer
                # to react anyway
                time.sleep(0.5)
            
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug(("Repetitively checking persistent tag " + 
                                    "'{}' as a short").format(id_))
            while DM is not None:
                s, v = DM.GetPersistentTagGroup().GetTagAsShort(id_)

                if s:
                    index = v
                    DM.GetPersistentTagGroup().DeleteTagWithLabel(id_)
                    if do_log(self._logger, logging.DEBUG):
                        self._logger.debug(("Found tag '{}' with value '{}', " + 
                                            "deleted it now.").format(id_, v))
                    break
                
                time.sleep(0.1)
        
        if 0 <= index and index < len(options):
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("User was asked '{}' and clicked '{}'".format(
                                text, options[index]))
            return index
        else:
            err = StopProgram()
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Stopping program", exc_info=err)
            raise err
    
    def askFor(self, *inputs: AskInput, **kwargs) -> tuple:
        """Ask for the specific input when the program needs to know something 
        from the user. 
        
        The following indices are supported for the `inputs`:
        - 'name' : str, required - The name of the input to show
        - 'datatype' : type or Datatype - The datatype to allow
        - 'description' : str - A description what this value is about
        
        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        inputs : dict
            A dict with the 'name' key that defines the name to show. Optional
            additional keys are 'datatype' and 'description'
        
        Keyword Args
        ------------
        text : str
            The text to show when the input lines pop up, default:
            "Please enter the following values."
        
        Returns
        -------
        tuple
            A tuple of values where the value on index 0 is the value for the 
            `inputs[0]` and so on
        """

        if "text" not in kwargs:
            if len(inputs) > 1:
                kwargs["text"] = "Please enter the following values"
            else:
                kwargs["text"] = "Please enter the value"
        
        results = self._showDialog(
            ask_for_values=inputs, 
            ask_for_msg=kwargs["text"],
            dialog_type=0b100
        )

        if len(results) <= 3 or results[3] is None:
            err = RuntimeError("Could not create the resulting ask values from " + 
                               "the dialogs values.")
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("{}: {}".format(err.__class__.__name__, err))
            raise err

        if do_log(self._logger, logging.DEBUG):
            self._logger.debug(("User was asked for values '{}' with kwargs " + 
                                "'{}' and entered '{}'").format(inputs, kwargs, 
                                results[3]))
        return results[3]
    
    def clear(self) -> None:
        """Clear the current text output."""
        self._out = ""

    def print(self, *values: object, sep: typing.Optional[str]=" ", 
              end: typing.Optional[str]="\n", inset: typing.Optional[str]="") -> None:
        """Print a line to the user.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        values : str or object
            The value to print
        sep : str
            The separator between two values, default: " "
        end : str
            The end character to end a line, default: "\n"
        inset : str, optional
            Some characters to print before every line, default: ""
        """
        text = inset + sep.join(map(str, values)) + end
        text = textwrap.wrap(text, self.line_length, drop_whitespace=False,
                             replace_whitespace=False)
        text = ("\n" + inset).join(text)

        self._out += text
        # self._out = text + self._out
        self._updateRunning()
    
    def _createKillDialog(self) -> None:
        """A dialog that shows the kill button only."""

        id_ = int(time.time() * 100)
        dmscript = "\n".join((
            "class handler_{} : UIFrame {{".format(id_),
            "void killTaks(object self){",
            "if(!GetPersistentTagGroup().TagGroupDoesTagExist(\"{}\")){{".format(self._progress_dialog_kill_tagname),
            "GetPersistentTagGroup().TagGroupCreateNewLabeledTag(\"{}\");".format(self._progress_dialog_kill_tagname),
            "}",
            "GetPersistentTagGroup().TagGroupSetTagAsBoolean(\"{}\", 1);".format(self._progress_dialog_kill_tagname),
            "}",
            "}",
            "TagGroup Dialog = DLGCreateDialog(\"Kill task\");",
            "TagGroup kill_button = DLGCreatePushButton(\"Kill Task\", \"killTaks\");",
            "Dialog.DLGAddElement(kill_button);",
            "object kill_dialog = alloc(handler_{}).init(Dialog)".format(id_),
            "kill_dialog.display(\"Kill task\");",
        ))
        self._created_tagnames.add(self._progress_dialog_kill_tagname)

        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Creating kill dialg by executing dmscript '{}'")
        with execdmscript.exec_dmscript(dmscript, debug=self._exec_debug):
            pass
        
    def showRunning(self) -> None:
        """Show the progress dialog.
        
        Note: Make sure to set the `DMView.progress_max` before calling this 
        function!
        """

        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Showing running indicator")
        running = self.show_running
        super().showRunning()

        if not running:
            id_ = int(time.time() * 100)
            self._progress_dialog_progress_tagname = "__pylo_dm_view_progress_{}".format(
                id_
            )
            self._progress_dialog_text_tagname = "__pylo_dm_view_text_{}".format(
                id_
            )
            self._progress_dialog_success_tagname = "__pylo_dm_view_success_{}".format(
                id_
            )
            self._progress_dialog_kill_tagname = "__pylo_dm_view_kill_{}".format(
                id_
            )
            self._progress_dialog_success = None

            self._created_tagnames.add(self._progress_dialog_progress_tagname)
            self._created_tagnames.add(self._progress_dialog_success_tagname)
            self._created_tagnames.add(self._progress_dialog_text_tagname)
            self._created_tagnames.add(self._progress_dialog_kill_tagname)

            self.deleteObservedTags()
            self._updateRunning()
            # self._createKillDialog()
            self._createRunningDialog()
        
            # block the thread until the user pressed ok or cancel
            self._observeProgressDialogSuccessThread()
            self.deleteObservedTags()

        if self._progress_dialog_success <= 0:
            err = StopProgram()
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Stopping program", exc_info=err)
            raise err

    def _createRunningDialog(self) -> None:
        """Create and show the running dialog in another thread.
        
        Note: Make sure to set the `DMView.progress_max` before calling this 
        function!

        Notes
        -----
        This function creates a dialog that is running in the current dm-script
        main thread. UI components always run in the main thread!
        """
        path = os.path.join(self._rel_path, "dm_view_progress_dialog.s")
        sv = {
            "max_progress": self.progress_max,
            "progress_tn": self._progress_dialog_progress_tagname,
            "text_tn": self._progress_dialog_text_tagname,
            "success_tn": self._progress_dialog_success_tagname,
            "kill_tn": self._progress_dialog_kill_tagname
        }
        self._created_tagnames.add(self._progress_dialog_progress_tagname)
        self._created_tagnames.add(self._progress_dialog_success_tagname)
        self._created_tagnames.add(self._progress_dialog_text_tagname)
        
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug(("Showing running dialog by executing " + 
                                "dmscript '{}' with setvars '{}'").format(
                                path, sv))
        with execdmscript.exec_dmscript(path, setvars=sv, debug=self._exec_debug):
            pass
    
    def _observeProgressDialogSuccessThread(self) -> None:
        """Observe the persistent tag with the name 
        `DMView._progress_dialog_success_tagname` and set the 
        `DMView._progress_dialog_success` to the value as soon as the value is 
        present.
        """

        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Blocking thread until progress dialog is " + 
                               "done or cancelled.")
        while DM is not None and self.show_running:
            s, v = DM.GetPersistentTagGroup().GetTagAsShort(
                self._progress_dialog_success_tagname
            )
            
            if s:
                if do_log(self._logger, logging.DEBUG):
                    self._logger.debug(("Found success value '{}' in " +
                                        "persistent tag '{}'").format(
                                        v, self._progress_dialog_success_tagname))
                self._progress_dialog_success = v
                break
                
            s, v = DM.GetPersistentTagGroup().GetTagAsBoolean(
                self._progress_dialog_kill_tagname
            )

            if s and v:
                if do_log(self._logger, logging.DEBUG):
                    self._logger.debug(("Found kill value '{}' in " +
                                        "persistent tag '{}'").format(
                                        v, self._progress_dialog_kill_tagname))
                break
            
            time.sleep(0.05)
    
    def deleteObservedTags(self) -> None:
        """Delete all the observed tags."""
        if isinstance(self._progress_dialog_progress_tagname, str):
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Deleting persistent tag '{}'".format(
                                   self._progress_dialog_progress_tagname))
            execdmscript.remove_global_tag(self._progress_dialog_progress_tagname)
        
        if isinstance(self._progress_dialog_text_tagname, str):
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Deleting persistent tag '{}'".format(
                                   self._progress_dialog_text_tagname))
            execdmscript.remove_global_tag(self._progress_dialog_text_tagname)
        
        if isinstance(self._progress_dialog_success_tagname, str):
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Deleting persistent tag '{}'".format(
                                   self._progress_dialog_success_tagname))
            execdmscript.remove_global_tag(self._progress_dialog_success_tagname)
        
        if isinstance(self._progress_dialog_kill_tagname, str):
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Deleting persistent tag '{}'".format(
                                   self._progress_dialog_kill_tagname))
            execdmscript.remove_global_tag(self._progress_dialog_kill_tagname)
    
    def hideRunning(self) -> None:
        """Hides the progress dialog."""
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Hiding running dialog")
        self.deleteObservedTags()

        self._progress_dialog_progress_tagname = None
        self._progress_dialog_text_tagname = None
        self._progress_dialog_success_tagname = None
        self._progress_dialog_kill_tagname = None

        self._progress_dialog_success = None

        super().hideRunning()

    def _updateRunning(self) -> None:
        """Update the running indicator, the progress has updated."""
        if DM is not None:
            if self._progress_dialog_progress_tagname is not None:
                if do_log(self._logger, logging.DEBUG):
                    self._logger.debug(("Setting persistent tag '{}' to long " + 
                                        "value '{}'").format(
                                        self._progress_dialog_progress_tagname,
                                        self.progress))
                DM.GetPersistentTagGroup().SetTagAsLong(
                    self._progress_dialog_progress_tagname, self.progress
                )
            
            if self._progress_dialog_text_tagname is not None:
                if do_log(self._logger, logging.DEBUG):
                    self._logger.debug(("Setting persistent tag '{}' to string " + 
                                        "value '{}'").format(
                                        self._progress_dialog_text_tagname,
                                        self._out))
                DM.GetPersistentTagGroup().SetTagAsString(
                    self._progress_dialog_text_tagname, self._out
                )
            
            self._created_tagnames.add(self._progress_dialog_progress_tagname)
            self._created_tagnames.add(self._progress_dialog_text_tagname)
    
    def showProgramDialogs(self, controller: "Controller") -> typing.Tuple[typing.Tuple[dict, dict], dict, dict]:
        """Show the measurement creation, the configuration and the custom
        tags.
        
        Parameters:
        -----------
        controller : Controller
            The current controller for the microsocpe and the allowed 
            measurement variables
        
        Returns
        -------
        tuple of dicts, dict, dict
            The start and the series at index 0, the configuration at index 1 
            and the tags at index 2 in the way defined by the individual 
            functions
        """
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Showing all program dialogs")
        
        results = self._showDialog(
            measurement_variables=controller.microscope.supported_measurement_variables,
            configuration=controller.configuration,
            custom_tags=self._getCustomTagsFromConfiguration(controller.configuration),
            dialog_type=0b10 | 0b01 | 0b100
        )

        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Results of all dialogs are '{}'".format(results))

        if len(results) > 0:
            start = results[0]
        else:
            start = None
        
        if len(results) > 1:
            series = results[1]
        else:
            series = None
        
        if len(results) > 2:
            configuration = results[2]
        else:
            configuration = None
        
        if len(results) > 4:
            custom_tags = self._convertCustomTagsToDict(controller.configuration, 
                                                        results[4], 
                                                        save_to_config=True)
        else:
            custom_tags = None

        return start, series, configuration, custom_tags
    
    def showCreateMeasurement(self, controller: "Controller") -> typing.Tuple[dict, dict]:
        """Show the dialog for creating a measurement.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        RuntimeError
            When the dialog returns unparsable values
        
        Parameters:
        -----------
        controller : Controller
            The current controller for the microsocpe and the allowed 
            measurement variables

        Returns
        -------
        dict, dict
            A dict that defines the start conditions of the measurement where 
            each `MeasurementVariable`s ids as a key and the value is the start 
            value (value has to be the uncalibrated value)
            Another dict that contains the series with a 'variable', 'start', 
            'end' and 'step-width' key and an optional 'on-each-point' key that 
            may contain another series (value has to be the uncalibrated value)
        """
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Showing measurement")
        
        results = self._showDialog(
            measurement_variables=controller.microscope.supported_measurement_variables,
            configuration=controller.configuration,
            dialog_type=0b10
        )

        if len(results) > 0:
            start = results[0]
        else:
            start = None
        
        if len(results) > 1:
            series = results[1]
        else:
            series = None

        if start is None or series is None:
            if start is None and series is None:
                err = RuntimeError("Neither the start nor the series could " + 
                                   "be created from the dialogs values.")
            elif start is None:
                err = RuntimeError("The start could not be created from " + 
                                   "the dialogs values.")
            else:
                err = RuntimeError("The series could not be created from " + 
                                   "the dialogs values.")
            log_error(self._logger, err)
            raise err
        
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Returning start '{}' and series '{}'".format(
                               start, series))

        return start, series
    
    def showSettings(self, configuration: "AbstractConfiguration", 
                     keys: dict=None,
                     set_in_config: typing.Optional[bool]=True) -> dict:
        """Show the settings to the user.
        
        The `keys` can be a dict that contains dicts at each index. The index 
        of the outer dict is treated as the group, the index of the inner group
        is the key. The value will be set as the current value to the inputs.
        
        When the dialog is confirmed the settings_changed event is fired and 
        the new settings are returned. If `set_in_config` is True the settings 
        will also be applied to the configuration.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        RuntimeError
            When the dialog returns unparsable values
        
        Parameters
        ----------
        keys : Sequence of tuples, optional
            A list of tuples where index 0 contains the group and index 1
            contains the key name of the settings to show. The definitions are 
            loaded from the configuration, if not given all keys are shown
        set_in_config : bool, optional
            Whether to apply the settings to the configuration if confirmed,
            default: True
        
        Returns
        -------
        dict of dict
            A dict that contains the groups as keys, as the value there is 
            another dict for the keys in that group, the value is the newly set
            value
        """
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Showing settings")
        
        results = self._showDialog(configuration=configuration, dialog_type=0b01)

        if len(results) <= 2 or results[2] is None:
            err = RuntimeError("Could not create the configuration from " + 
                               "the dialogs values.")
            log_error(self._logger, err)
            raise err
            
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Returning settings '{}'".format(results[2]))

        return results[2]
    
    def _showCustomTags(self, tags: typing.Dict[str, typing.Dict[str, typing.Any]]) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        """Show the custom tags.

        The `tags` is a dict of dicts. Each key is the name of a tag to add.
        The value is a dict with the following indices:
        - "value": any, the value of the key to write in each image
        - "save": bool, whether to save the key into the configuration or not
        
        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        tags : dict of dicts
            The tags dict where the keys are the tag names and the values are 
            dicts with the "value" and "save" indices
        
        Returns
        -------
        dict
            The `tags` parameter dict modified by the user
        """
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Showing custom tags")
        
        results = self._showDialog(custom_tags=tags, dialog_type=0b1000)

        if len(results) <= 4 or results[4] is None:
            err = RuntimeError("Could not create the tags from " + 
                               "the dialogs values.")
            log_error(self._logger, err)
            raise err
            
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Returning tags '{}'".format(results[4]))

        return results[4]
    
    def _showDialog(self, 
                    measurement_variables: typing.Optional[typing.Union[list, dict]]=None, 
                    configuration: typing.Optional[AbstractConfiguration]=None, 
                    ask_for_values: typing.Optional[typing.Sequence[AskInput]]=None,
                    ask_for_msg: typing.Optional[str]="",
                    custom_tags: typing.Optional[dict]={},
                    dialog_type: typing.Optional[int]=0b11):
        """Show the dm-script dialog.

        Parameters
        ----------
        dialog_type : int, optional
            Define which dialog to show, use
            - `0b01` for showing the configuration dialog
            - `0b10` for showing the series dialog
            - `0b01 | 0b10 | 0b1000 = 0b1011` for showing the series dialog 
              but the user can switch to the configuration dialog and the 
              custom tags dialog and back
            - `0b100` for showing the ask for dialog
            - `0b1000` for showing the custom tags dialog
        """

        if (dialog_type & 0b01) > 0 and (dialog_type & 0b10) > 0:
            dialog_startup = ""
        elif (dialog_type & 0b01) > 0:
            dialog_startup = "configuration"
        elif (dialog_type & 0b100) > 0:
            dialog_startup = "ask_for"
        elif (dialog_type & 0b1000) > 0:
            dialog_startup = "custom_tags"
        else:
            dialog_startup = "series"
        
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug(("Showing dialog with mode '{:b}' which is " + 
                                "converted to '{}' as a string value").format(
                                dialog_type, dialog_startup))
        
        if isinstance(measurement_variables, list):
            m_vars = {}
            for var in measurement_variables:
                m_vars[var.unique_id] = var
            measurement_variables = m_vars

        m_vars = []
        
        # add all measurement variables if there are some
        if isinstance(measurement_variables, dict):
            var_keys = ("unique_id", "name", "unit", "min_value", "max_value",
                        "start", "end", "step")
            num_keys = ("start", "step", "end", "min_value", "max_value")
            for var in measurement_variables.values():
                m_var = {}

                for name in var_keys:
                    if name == "start":
                        if var.min_value == None:
                            val = 0
                        else:
                            val = var.min_value
                    elif name == "end":
                        if var.max_value == None:
                            val = 100
                        else:
                            val = var.max_value
                    elif name == "step":
                        if (var.min_value == None or var.max_value == None or 
                            var.min_value == var.max_value):
                            val = 1
                        else:
                            val = "{:.4}".format(
                                abs(var.min_value - var.max_value) / 10
                            )
                    else:
                        val = getattr(var, name)
                    
                    if val == None:
                        val = ""
                    elif not isinstance(val, (bool, str, float, int)):
                        val = str(val)
                    
                    m_var[name] = val

                    if name in num_keys and val != "":
                        if (var.format != None and var.format != str and 
                            hasattr(var.format, "format") and 
                            callable(var.format.format)):
                            m_var["formatted_{}".format(name)] = (
                                var.format.format(val)
                            )
                
                if isinstance(var.format, OptionDatatype):
                    m_var["format"] = "options"
                    m_var["options"] = var.format.options
                elif var.format != None:
                    m_var["format"] = get_datatype_name(var.format)
                
                m_vars.append(m_var)
        
        config_vars = {}
        if isinstance(configuration, AbstractConfiguration):
            for group in configuration.getGroups():
                if (not group in config_vars or not 
                    isinstance(config_vars[group], dict)):
                    config_vars[group] = {}

                for key in configuration.getKeys(group):
                    try:
                        val = configuration.getValue(group, key)
                    except KeyError:
                        val = ""
                    
                    try:
                        var_type = configuration.getDatatype(group, key)
                    except KeyError:
                        var_type = str
                    
                    if isinstance(var_type, OptionDatatype):
                        var_type_name = "options"
                    else:
                        var_type_name = get_datatype_name(var_type)

                    val = parse_value(var_type, val)
                    
                    try:
                        default_value = configuration.getDefault(group, key)
                    except KeyError:
                        default_value = ""
                    
                    try:
                        description = configuration.getDescription(group, key)
                    except KeyError:
                        description = ""
                    
                    try:
                        ask_if_not_present = configuration.getAskIfNotPresent(group, key)
                    except KeyError:
                        ask_if_not_present = False
                    
                    try:
                        restart_required = configuration.getRestartRequired(group, key)
                    except KeyError:
                        restart_required = False
                    
                    config_vars[group][key] = {
                        "value": val,
                        "default_value": default_value,
                        "datatype": var_type_name,
                        "description": str(description),
                        "ask_if_not_present": ask_if_not_present,
                        "restart_required": restart_required,
                    }

                    if isinstance(var_type, OptionDatatype):
                        config_vars[group][key]["options"] = var_type.options
        
        ask_vals = []
        if isinstance(ask_for_values, (tuple, list)):
            for input_definition in ask_for_values:
                if "datatype" in input_definition:
                    if isinstance(input_definition["datatype"], OptionDatatype):
                        input_definition["options"] = input_definition["datatype"].options
                        input_definition["datatype"] = "options"
                    elif not isinstance(input_definition["datatype"], str):
                        if hasattr(input_definition["datatype"], "name"):
                            input_definition["datatype"] = input_definition["datatype"].name
                        elif hasattr(input_definition["datatype"], "__name__"):
                            input_definition["datatype"] = input_definition["datatype"].__name__
                        else:
                            input_definition["datatype"] = str(input_definition["datatype"])
                    else:
                        input_definition["datatype"] = "string"
                else:
                    input_definition["datatype"] = "string"
            
                ask_vals.append(input_definition)

        variables = {
            "m_vars": m_vars,
            "config_vars": config_vars,
            "ask_vals": ask_vals,
            "message": ask_for_msg,
            "dialog_startup": dialog_startup,
            "custom_tag_vals": custom_tags
        }

        path = os.path.join(self._rel_path, "dm_view_dialog.s")
        sync_vars = {"start": dict, 
                     "series": dict, 
                     "configuration": dict, 
                     "ask_for": list,
                     "custom_tags": dict,
                     "success": bool}
        libs = (os.path.join(self._rel_path, "pylolib.s"), )

        start = None
        series = None
        config = None
        ask_for_values = None
        custom_tags = None
        success = None

        if do_log(self._logger, logging.DEBUG):
            self._logger.debug(("Executing dm libs '{}' and dmscript '{}' " + 
                                "with readvars '{}' and setvars '{}'").format(
                                libs, path, sync_vars, variables))

        # shows the dialog (as a dm-script dialog) in dm_view_series_dialog.s
        # and sets the start and series variables
        with execdmscript.exec_dmscript(*libs, path, readvars=sync_vars, 
                                        setvars=variables, 
                                        debug=self._exec_debug) as script:
            try:
                success = bool(script["success"])
            except KeyError:
                success = False

            if isinstance(measurement_variables, dict):
                try:
                    start = script["start"]
                except KeyError:
                    start = None
                
                if start is not None:
                    start, errors = self.parseStart(
                        measurement_variables, start, add_defaults=False,
                        parse=True, uncalibrate=True
                    )

            if isinstance(measurement_variables, dict):
                try:
                    series = script["series"]
                except KeyError:
                    series = None
                
                if series is not None:
                    series, errors = self.parseSeries(
                        measurement_variables, series, add_defaults=False,
                        parse=True, uncalibrate=True
                    )

            try:
                config = script["configuration"]
            except KeyError:
                config = None
            
            try:
                ask_for_values = script["ask_for"]
            except KeyError:
                ask_for_values = None
            
            try:
                custom_tags = script["custom_tags"]
            except KeyError:
                custom_tags = None
        
        if success and ((start is not None and series is not None) or 
           config is not None or ask_for_values is not None or 
           custom_tags is not None):
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug(("Returning start '{}', series '{}', " + 
                                    "config '{}', ask_for_values '{}' and " + 
                                    "custom_tags '{}'").format(start, series,
                                    config, ask_for_values, custom_tags))
            return start, series, config, ask_for_values, custom_tags
        else:
            err = StopProgram()
            if do_log(self._logger, logging.DEBUG):
                self._logger.debug("Stopping program", exc_info=err)
            raise err
        
    def __del__(self):
        """Make sure that all added persistent tagnames are removed again."""

        for tagname in self._created_tagnames:
            if isinstance(tagname, str):
                if do_log(self._logger, logging.DEBUG):
                    self._logger.debug("Deleting persistent tag '{}'".format(tagname))
                execdmscript.remove_global_tag(tagname)