/**
 * The dialog to show for the configuration.
 */
class DMViewConfigurationDialog : UIFrame{
    /**
     * The `configuration` as a `TagGroup`, each key is the group, the value is another TagGroup 
     * with the keys and the 'value', 'datatype', 'default_value', 'ask_if_not_present', 
     * 'description' and 'restart_required' keys.
     */
    TagGroup configuration;

    /**
     * The label that displays the error messages if there are some.
     */
    TagGroup error_display;

    /**
     * All inputs in a `TagList`
     */
    TagGroup inputs;

    /**
     * Returns whether the current `UIFrame` is displayed or not.
     *
     * @return 
     *      1 if the dialog is shown, 0 if not
     */
    number isShown(object self){
        number t, l, b, r;
        self.GetFrameBounds(t, l, b, r);

        if(t == 0 && l == 0 && b == 0 && r == 0){
            // if the dialog is not shown, all values are 0
            return 0;
        }
        else{
            return 1;
        }
    }

    /**
     * Get the `group`, the `key` and the input `index` for the `identifier`.
     *
     * The values are taken from the identifier by splitting by "/".
     *
     * @param identifier
     *      The identifier
     * @param group
     *      The reference to save the group to
     * @param key
     *      The reference to save the key to
     * @param index
     *      The reference to save the index to
     *
     * @return 
     *      1 if the `identifier` was parsed successfully, 0 if not
     */
    number parseIdentifier(object self, string identifier, string &group, string &key, number &index){
        number p = -1;

        p = identifier.find("/");
        group = identifier.left(p);
        identifier = identifier.right(identifier.len() - p - 1);

        p = identifier.find("/");
        key = identifier.left(p);
        identifier = identifier.right(identifier.len() - p - 1);

        if(group != "" && key != "" && is_numeric(identifier)){
            index = identifier.val();
            return 1;
        }
        else{
            group = "";
            key = "";
            index = -1;
            return 0;
        }
    }

    /**
     * Validate the text inside the `input`. The `type` tells which input type the `input` is. It
     * can be the following:
     * - "start_value": A start parameter input box
     * - "series_start": A start value of a series
     * - "series_step_width": A step width value of a series
     * - "series_end": An end value of a series
     *
     * This function also checks if the start is less than the end if either a start or an end value
     * is given and if the step width is less than the maximum span of numbers (end - start).
     *
     * The `errors` will contain error messages separated by "\n".
     *
     * If the `type` is not valid, 0 will be returned but no errors will be set to the `errors`.
     *
     * @param type
     *      The type of the `input`, use "start_value", "series_start", "series_step_width" or 
     *      "series_end"
     * @param input
     *      The dialog input field
     * @param errors
     *      The variable to save the errors to, all errors are separated by "\n"s.
     *
     * @return
     *      1 if the value is valid, 0 if not
     */
    number _validateInput(object self, TagGroup input, string &errors){
        number valid = 1;

        // string identifier;
        // input.DLGGetIdentifier(identifier);

        // number pos = identifier.find("/");
        // string group = identifier.left(pos);

        // identifier = identifier.right(identifier.len() - pos);
        // number pos = identifier.find("/");
        // string key = identifier.left(pos);

        // TagGroup group_tg;
        // configuration.TagGroupGetTagAsTagGroup(group, group_tg);

        // TagGroup value_tg;
        // group_tg.TagGroupGetTagAsTagGroup(key, value_tg);)
        
        return valid;
    }

    /**
     * Validates all inputs.
     */
    number validateInputs(object self, string &errors){
        number valid = 1;
        errors = "";

        for(number j = 0; j < inputs.TagGroupCountTags(); j++){
            TagGroup input;
            string input_error = "";

            inputs.TagGroupGetIndexedTagAsTagGroup(j, input);
            input_error = ""
            valid = valid && self._validateInput(input, input_error);
            errors += input_error;
        }

        return valid;
    }

    /**
     * Create the content for the configuration panel.
     *
     * @return
     *      The configuration content as a dialog group
     */
    TagGroup _createConfigurationContent(object self){
        TagGroup wrapper = DLGCreateGroup();

        // TagGroup error_headline = DLGCreateLabel("Errors:");
        // wrapper.DLGAddElement(error_headline);
        TagGroup error_box = DLGCreateBox("Errors");

        error_display = DLGCreateLabel("Currently no errors", 130);
        error_display.DLGHeight(2);
        error_display.DLGExpand("X");
        error_display.DLGFill("X");
        // wrapper.DLGAddElement(error_display);
        error_box.DLGAddElement(error_display);
        wrapper.DLGAddElement(error_box);

        // save all start value input boxes in a group
        inputs = NewTagList();

        // the number of variables to show in one row
        number max_cols = 1;
        number max_rows = 7;

        // column widths
        number cw1 = 20; // label column
        number cw2 = 40; // value column
        number cw3 = 60; // value column

        TagGroup tabs = DLGCreateTabList();
        tabs.DLGExpand("X");
        tabs.DLGFill("X");

        number counter = 0;
        number row_counter = 0;
        number page_counter = 0;
        TagGroup tab = DLGCreateTab("Page " + (page_counter + 1))

        for(number i = 0; i < configuration.TagGroupCountTags(); i++){
            String group = configuration.TagGroupGetTagLabel(i);
            TagGroup group_values;
            configuration.TagGroupGetTagAsTagGroup(group, group_values);

            number remaining_rows = max_rows - row_counter
            number group_rows = ceil(group_values.TagGroupCountTags() / max_cols);
            if(remaining_rows < group_rows && group_rows < max_rows && (remaining_rows < 3 || group_rows - remaining_rows < 3)){
                // required rows (group_rows) do not all fit in the current tab, create a new tab
                // if
                // 1. The group can fit on one page
                // 2. There are less than 3 elements on this tab or there will be less than 3 on the
                //    next page
                row_counter = 0;
                page_counter++;
                tabs.DLGAddTab(tab);
                tab = DLGCreateTab("Page " + (page_counter + 1));
                tab.DLGExpand("X");
                tab.DLGFill("X");
            }

            TagGroup group_box = DLGCreateBox(group);
            group_box.DLGExpand("X");
            group_box.DLGFill("X");
            group_box.DLGAnchor("West");
            if(max_cols > 1){
                group_box.DLGTableLayout(max_cols, min(group_rows, remaining_rows), 0);
            }

            for(number j = 0; j < group_values.TagGroupCountTags(); j++){
                string key = group_values.TagGroupGetTagLabel(j);

                TagGroup value_settings;
                group_values.TagGroupGetTagAsTagGroup(key, value_settings);

                string description;
                string type;
                value_settings.TagGroupGetTagAsString("description", description);
                value_settings.TagGroupGetTagAsString("datatype", type);

                TagGroup value_wrapper = DLGCreateGroup();

                TagGroup line = DLGCreateGroup();
                line.DLGTableLayout(3, 1, 0);
                line.DLGExpand("X");
                line.DLGAnchor("East");
                line.DLGFill("X");

                if(type != "boolean"){
                    TagGroup label = DLGCreateLabel(key, cw1);
                    label.DLGAnchor("North");
                    line.DLGAddElement(label);
                }

                TagGroup input;
                if(type == "int"){
                    number value;
                    value_settings.TagGroupGetTagAsLong("value", value);
                    input = DLGCreateIntegerField(round(value), cw2);
                }
                else if(type == "float"){
                    number value;
                    value_settings.TagGroupGetTagAsFloat("value", value);
                    input = DLGCreateRealField(value, cw2, 4);
                }
                else if(type == "boolean"){

                    number value;
                    value_settings.TagGroupGetTagAsBoolean("value", value);
                    input = DLGCreateCheckBox(key, value != 0 ? 1 : 0);
                    input.DLGAnchor("East");

                    TagGroup inner_line_wrapper = DLGCreateGroup();
                    // inner_line_wrapper.DLGWidth(cw1 + cw2);
                    inner_line_wrapper.DLGAddElement(input);
                    inner_line_wrapper.DLGAnchor("East");
                    inner_line_wrapper.DLGSide("Right");
                    line.DLGAddElement(inner_line_wrapper);
                }
                else{
                    string value;
                    value_settings.TagGroupGetTagAsString("value", value);
                    input = DLGCreateStringField(value, cw2);
                }

                input.DLGIdentifier(group + "/" + key + "/" + counter);

                if(type != "boolean"){
                    input.DLGAnchor("North");
                    line.DLGAddElement(input);
                }

                TagGroup description_label = DLGCreateLabel(description, cw3);
                description_label.DLGHeight(ceil(description.len() / 55));
                description_label.DLGAnchor("East");
                line.DLGAddElement(description_label);

                inputs.TagGroupInsertTagAsTagGroup(infinity(), input);

                value_wrapper.DLGAddElement(line);
                group_box.DLGAddElement(value_wrapper);
                counter++;

                row_counter++;

                if(row_counter > max_rows){
                    row_counter = 0;
                    page_counter++;
                    tabs.DLGAddTab(tab);
                    tab = DLGCreateTab("Page " + (page_counter + 1));
                    tab.DLGExpand("X");
                    tab.DLGFill("X");
                    tab.DLGAnchor("West");
                }
            }

            tab.DLGAddElement(group_box);
        }
        
        tabs.DLGAddTab(tab);

        TagGroup inputs_wrapper = DLGCreateGroup();
        inputs_wrapper.DLGAddElement(tabs);
        inputs_wrapper.DLGAnchor("West");
        inputs_wrapper.DLGExpand("X");
        inputs_wrapper.DLGFill("X");

        wrapper.DLGAddElement(inputs_wrapper);
        // wrapper.DLGExpand("X");
        // wrapper.DLGFill("X");

        return wrapper;
    }

	/**
	 * Create the contents of the dialog. 
     *
     * @param title
     *      The title of the dialog
     * @param message
     *      The message, use "" for not showing a message.
	 *
	 * @return
	 *		The dialogs contents as a TagGroup for initializing an
	 *		UIFrame
	 */
	TagGroup _createContent(object self, string title, string message){
		TagGroup dialog_items;
		TagGroup dialog_tags = DLGCreateDialog(title, dialog_items);

        if(message != ""){
            // description text
            TagGroup label = DLGCreateLabel(message, 130);
            label.DLGHeight(1);
            dialog_items.DLGAddElement(label);
        }
        
        dialog_items.DLGAddElement(self._createConfigurationContent());

		return dialog_tags;
    }
	
    /**
     * Create a new dialog.
     *
     * @param title
     *      The title of the dialog
     * @param message
     *      The message, use "" for not showing a message.
     *
     * @return
     *      The dialog
     */
	object init(object self, string title, TagGroup config_vars, string message){
        configuration = config_vars;
		self.super.init(self._createContent(title, message));
        
		return self;
	}

    /**
     * Overwriting pose function, before clicking 'OK' the inputs are validated. If there are errors
     * an error dialog is shown.
     */
    number pose(object self){
        if(self.super.pose()){
            // string errors;
            // if(self.validateInputs(errors) != 1){
            //     // showAlert("There are the following errors in the current series: \n\n" + errors + "\n\nEither fix them or press 'Cancel'.", 0);
            //     error_display.DLGTitle(errors);
            //     return self.pose();
            // }
            // else{
                return 1;
            // }
        }
        else{
            return 0;
        }
    }

    /**
     * Get the configuration as a `TagGroup`.
     *
     * @return
     *      The configuration `TagGroup`
     */
    TagGroup getConfiguration(object self){
        TagGroup config_vars = NewTagGroup();

        for(number j = 0; j < inputs.TagGroupCountTags(); j++){
            TagGroup input;
            string input_error = "";

            inputs.TagGroupGetIndexedTagAsTagGroup(j, input);

            string identifier;
            input.DLGGetIdentifier(identifier);
            
            string group;
            string key;
            number index;
            
            if(self.parseIdentifier(identifier, group, key, index)){
                TagGroup group_tg;
                if(config_vars.TagGroupDoesTagExist(group) != 0){
                    config_vars.TagGroupGetTagAsTagGroup(group, group_tg);
                }

                if(group_tg.TagGroupIsValid() == 0){
                    group_tg = NewTagGroup();
                    number i = config_vars.TagGroupCreateNewLabeledTag(group);
                    config_vars.TagGroupSetIndexedTagAsTagGroup(i, group_tg);
                }
                
                string value = input.DLGGetStringValue();
                number k = group_tg.TagGroupCreateNewLabeledTag(key);
                group_tg.TagGroupSetIndexedTagAsString(k, value);
            }
        }

        return config_vars;
    }
}

// config_vars are defined in the python file executing this file
TagGroup config_vars = NewTagGroup();

number index;
TagGroup tg, tg2;

tg = NewTagGroup();

tg2 = NewTagGroup();
index = tg2.TagGroupCreateNewLabeledTag("value");
tg2.TagGroupSetIndexedTagAsString(index, "camera");
index = tg2.TagGroupCreateNewLabeledTag("default_value");
tg2.TagGroupSetIndexedTagAsString(index, "");
index = tg2.TagGroupCreateNewLabeledTag("datatype");
tg2.TagGroupSetIndexedTagAsString(index, "string");
index = tg2.TagGroupCreateNewLabeledTag("description");
tg2.TagGroupSetIndexedTagAsString(index, "the detector to use to acquire the image");
index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg2.TagGroupCreateNewLabeledTag("restart_required");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg.TagGroupCreateNewLabeledTag("detector-name");
tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

tg2 = NewTagGroup();
index = tg2.TagGroupCreateNewLabeledTag("value");
tg2.TagGroupSetIndexedTagAsNumber(index, 1024);
index = tg2.TagGroupCreateNewLabeledTag("default_value");
tg2.TagGroupSetIndexedTagAsString(index, "");
index = tg2.TagGroupCreateNewLabeledTag("datatype");
tg2.TagGroupSetIndexedTagAsString(index, "int");
index = tg2.TagGroupCreateNewLabeledTag("description");
tg2.TagGroupSetIndexedTagAsString(index, "the size (width has to be equal to height) of the image the detector makes in px");
index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg2.TagGroupCreateNewLabeledTag("restart_required");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg.TagGroupCreateNewLabeledTag("image-size");
tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

index = config_vars.TagGroupCreateNewLabeledTag("pyjem-camera");
config_vars.TagGroupSetIndexedTagAsTagGroup(index, tg);

tg = NewTagGroup();

tg2 = NewTagGroup();
index = tg2.TagGroupCreateNewLabeledTag("value");
tg2.TagGroupSetIndexedTagAsBoolean(index, 1);
index = tg2.TagGroupCreateNewLabeledTag("default_value");
tg2.TagGroupSetIndexedTagAsString(index, "");
index = tg2.TagGroupCreateNewLabeledTag("datatype");
tg2.TagGroupSetIndexedTagAsString(index, "boolean");
index = tg2.TagGroupCreateNewLabeledTag("description");
tg2.TagGroupSetIndexedTagAsString(index, "Whether to set the microscope in the safe sate after the measurement is finished");
index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg2.TagGroupCreateNewLabeledTag("restart_required");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg.TagGroupCreateNewLabeledTag("microscope-to-safe-state-after-measurement");
tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

tg2 = NewTagGroup();
index = tg2.TagGroupCreateNewLabeledTag("value");
tg2.TagGroupSetIndexedTagAsFloat(index, 3.5);
index = tg2.TagGroupCreateNewLabeledTag("default_value");
tg2.TagGroupSetIndexedTagAsString(index, "");
index = tg2.TagGroupCreateNewLabeledTag("datatype");
tg2.TagGroupSetIndexedTagAsString(index, "float");
index = tg2.TagGroupCreateNewLabeledTag("description");
tg2.TagGroupSetIndexedTagAsString(index, "The relaxation time in seconds to wait after the microscope is switched to lorenz mode. Use 0 or negative values to ignore");
index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg2.TagGroupCreateNewLabeledTag("restart_required");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg.TagGroupCreateNewLabeledTag("relaxation-time-lorenz-mode");
tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

string path = GetApplicationDirectory("auto_save", 1)
tg2 = NewTagGroup();
index = tg2.TagGroupCreateNewLabeledTag("value");
tg2.TagGroupSetIndexedTagAsString(index, path + "\\1990-01-01\\");
index = tg2.TagGroupCreateNewLabeledTag("default_value");
tg2.TagGroupSetIndexedTagAsString(index, "");
index = tg2.TagGroupCreateNewLabeledTag("datatype");
tg2.TagGroupSetIndexedTagAsString(index, "string");
index = tg2.TagGroupCreateNewLabeledTag("description");
tg2.TagGroupSetIndexedTagAsString(index, "The directory where to save the camera images to that are recorded while measuring");
index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg2.TagGroupCreateNewLabeledTag("restart_required");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg.TagGroupCreateNewLabeledTag("save-directory");
tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

tg2 = NewTagGroup();
index = tg2.TagGroupCreateNewLabeledTag("value");
tg2.TagGroupSetIndexedTagAsString(index, "{counter}_{time:%Y-%m-%d_%H-%M-%S}_lorenz-measurement.dm4");
index = tg2.TagGroupCreateNewLabeledTag("default_value");
tg2.TagGroupSetIndexedTagAsString(index, "");
index = tg2.TagGroupCreateNewLabeledTag("datatype");
tg2.TagGroupSetIndexedTagAsString(index, "string");
index = tg2.TagGroupCreateNewLabeledTag("description");
tg2.TagGroupSetIndexedTagAsString(index, "The name format to use to save the recorded images. Some placeholders can be used. Use {counter} to get the current measurement number, use {tags[your_value]} to get use the `your_value` of the measurement tags. Use {variables[your_variable]} to get the value of the measurement variable `your_variable`. To use the `your_img_value` of the image tags, use {imgtags[your_value]}. For times set the format according to the python `strftime()` format, started with a colon (:), like {time:%Y-%m-%d_%H-%M-%S} for year, month, day and hour minute and second. Make sure to inculde the file extension but use supported extensions only.");
index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg2.TagGroupCreateNewLabeledTag("restart_required");
tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
index = tg.TagGroupCreateNewLabeledTag("save-file-format");
tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

index = config_vars.TagGroupCreateNewLabeledTag("measurement");
config_vars.TagGroupSetIndexedTagAsTagGroup(index, tg);

// config_vars.TagGroupOpenBrowserWindow(0);

object dialog = alloc(DMViewConfigurationDialog).init("Lorenz mode measurement settings -- PyLo", config_vars, "Set the settings used for recording a new measurement.");

TagGroup configuration;

if(dialog.pose()){
    configuration = dialog.getConfiguration();
    // configuration.TagGroupOpenBrowserWindow(0);
}