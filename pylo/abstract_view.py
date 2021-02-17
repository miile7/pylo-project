import typing
import logging

from .datatype import Datatype
from .pylolib import parse_value
from .pylolib import human_concat_list
from .logginglib import log_debug
from .logginglib import get_logger

if hasattr(typing, "TypedDict"):
    AskInput = typing.TypedDict("AskInput", {
                                "datatype": typing.Union[type, Datatype],
                                "name": str
                                }, total=False)
else:
    AskInput = typing.Dict

class AbstractView:
    """This class defines the methods for the view.
    
    Attributes
    ----------
    progress_max : int
        The maximum number the progress can have
    progress : int
        The current progress
    """

    def __init__(self):
        """Get the view object."""
        self._logger = get_logger(self)
        self.show_running = False
        self.progress_max = 100
        self.progress = 0

    @property
    def progress(self):
        """The current progress."""
        return self.__progress

    @progress.setter
    def progress(self, progress : int) -> None:
        """Progress setter."""

        if progress < 0:
            self.__progress = 0
        elif progress > self.progress_max:
            self.__progress = self.progress_max
        else:
            self.__progress = progress
        
        log_debug(self._logger, "Setting progress to '{}' (was initially '{}')".format(
                               self.__progress, progress))
        
        if self.show_running:
            self._updateRunning()

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
        log_debug(self._logger, "Showing program dialogs")
        start, series = self.showCreateMeasurement(controller)
        configuration = self.showSettings(controller.configuration)
        custom_tags = self.showCustomTags(controller.configuration)

        return start, series, configuration, custom_tags

    def showCreateMeasurement(self, controller: "Controller",
                              series: typing.Optional[dict]=None,
                              start: typing.Optional[dict]=None) -> typing.Tuple[dict, dict]:
        """Show the dialog for creating a measurement.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters:
        -----------
        controller : Controller
            The current controller for the microsocpe and the allowed 
            measurement variables
        series : dict
            The series dict that defines the series that is shown on startup
            with uncalibrated and parsed values, if not given the default 
            values are used, default: None
        start : dict
            The series start definition that is shown on startup  with 
            uncalibrated and parsed values, if not given the default values are 
            used, default: None

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
        raise NotImplementedError()

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
        raise NotImplementedError()

    def showCustomTags(self, configuration: "AbstractConfiguration") -> typing.Dict[str, str]:
        """Show a view to let the user add custom tags to each image.
        
        Show all tags from the `custom-tags` group in the `configuration` and 
        let the user add more tags. Each tag has a key and a value and can be 
        saved persistently or not.

        When confirmed, the tags the user decided are saved and the function 
        returns all tags as a dict with the key as a string and the value as a
        string.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration
        
        Returns
        -------
        dict
            The custom tags as key-value pairs
        """
        
        log_debug(self._logger, "Showing custom tags dialog")
        tags = self._getCustomTagsFromConfiguration(configuration)
        tags = self._showCustomTags(tags)
        tags = self._convertCustomTagsToDict(configuration, tags, 
                                             save_to_config=True)
        log_debug(self._logger, "Found tags '{}'".format(tags))
        return tags

    def _getCustomTagsFromConfiguration(self, configuration: "AbstractConfiguration",
                                        additional_tags: typing.Optional[typing.Dict[str, typing.Any]]={}):
        """Get the custom tags from the configuration.

        If more tags should be added, the `additional_tags` can be set to a 
        dict containing the key-value pairs for the tags.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration
        tags : mapping
            The custom tags as key-value pairs
        
        Returns
        -------
        dict of dicts
            The tags dict where the keys are the tag names and the values are 
            dicts with the "value" and "save" indices
        """
        from .config import CUSTOM_TAGS_GROUP_NAME
        
        tags = {}

        try:
            additional_tags = dict(additional_tags)
        except TypeError:
            additional_tags = None
        
        if isinstance(additional_tags, dict):
            for key, value in additional_tags.items():
                additional_tags[key] = {"value": value, "save": False}
        
        try:
            for key in configuration.getKeys(CUSTOM_TAGS_GROUP_NAME):
                try:
                    value = configuration.getValue(CUSTOM_TAGS_GROUP_NAME, key)
                except KeyError:
                    value = ""
                tags[key] = {"value": value, "save": True}

                # reset complete group
                configuration.removeElement(CUSTOM_TAGS_GROUP_NAME, key)
        except KeyError:
            pass
        
        return tags
    
    def _convertCustomTagsToDict(self, configuration: "AbstractConfiguration", 
                                 tags: typing.Union[typing.Mapping[str, typing.Mapping[str, typing.Any]], typing.Any],
                                 save_to_config: typing.Optional[bool]=True) -> typing.Dict[str, str]:
        """Converts the `tags` to a dict.

        The `tags` is a dict where the tags key is the dict key and the value
        is a dict with the "value" and the "save" keys.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration
        tags : dict of dicts
            The tags dict where the keys are the tag names and the values are 
            dicts with the "value" and "save" indices, if a non-mapping is 
            given it is treated as an empty dict
        save_to_config : bool, optional
            Whether to save the tags with a True "save" index to the 
            configuration, default: True
        
        Returns
        -------
        dict
            The custom tags as key-value pairs
        """
        from .config import CUSTOM_TAGS_GROUP_NAME

        try:
            tags = dict(tags)
        except TypeError:
            tags = {}

        keys = list(tags.keys())
        for key in keys:
            if not "value" in tags[key] or tags[key]["value"] is None:
                del tags[key]
            elif not isinstance(tags[key]["value"], str):
                tags[key]["value"] = str(tags[key]["value"])
        
        if save_to_config:
            for key, tag in tags.items():
                if "save" in tag and tag["save"]:
                    configuration.setValue(CUSTOM_TAGS_GROUP_NAME, key, 
                                           tag["value"])
        
        return dict(zip(tags.keys(), map(lambda x: x["value"], tags.values())))
    
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
        raise NotImplementedError()

    def showHint(self, hint : str, **kwargs) -> None:
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
        raise NotImplementedError()

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
        raise NotImplementedError()

    def print(self, *values: object, sep: typing.Optional[str]=" ", end: typing.Optional[str]="\n") -> None:
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
        """
        raise NotImplementedError()

    def clear(self) -> None:
        """Clear the current text output."""
        raise NotImplementedError()
    
    def showRunning(self) -> None:
        """Show the progress bar and the outputs of the `AbstractView::print()`
        function.
        """
        log_debug(self._logger, "Showing a running indicator")
        self.show_running = True
    
    def hideRunning(self) -> None:
        """Hides the progress bar shown by `AbstractView::showRunning()`."""
        log_debug(self._logger, "Hiding the running indicator")
        self.show_running = False

    def _updateRunning(self) -> None:
        """Update the running indicator, the progress has updated."""
        raise NotImplementedError()

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
        raise NotImplementedError()

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
            additional keys are 'datatype', and 'description'
        
        Keyword Args
        ------------
        text : str
            The text to show when the input lines pop up, note that not all 
            views support this
        
        Returns
        -------
        tuple
            A tuple of values where the value on index 0 is the value for the 
            `inputs[0]` and so on
        """
        raise NotImplementedError()

    def _formatAskForInput(self, input_dict : AskInput) -> dict:
        """Format and check the `input_dict` used in `AbstractView::askFor()`.

        Raises
        ------
        KeyError
            When the "name" key is missing
        TypeError
            When the type of the key is wrong
        
        Parameters
        ----------
        input_dict : dict
            A dict with the 'name' key that defines the name to show. Optional
            additional keys are 'datatype', and 'description'
        
        Returns
        -------
        dict
            The same dict with valid keys only, if the value was None or empty
            the key is removed
        """

        if not "name" in input_dict:
            raise KeyError("There is no '{}' index given.".format("name"))

        for key, datatype in {"name": str, "datatype": (type, Datatype), 
                              "description": str}.items():
            if key in input_dict:
                if input_dict[key] is None:
                    del input_dict[key]
                elif not isinstance(input_dict[key], datatype):
                    raise TypeError(("The value for index '{}' has to be a {} " + 
                                    "but {} is given").format(key, datatype, 
                                    type(input_dict[key])))
        
        if "description" in input_dict and input_dict["description"] == "":
            del input_dict["description"]
        
        return input_dict