/**
 * The dialog to show for the series select and the settings.
 */
class DMViewDialog : UIFrame{
    /**
     * The `MeasurementVariable`s as a TagList. Each entry contains a TagGroup which represents the 
     * python `MeasurementVariable` object. Each attribute of the object can be received with the
     * same name in the TagGroup exteded with the `start`, `step_width` and `end` keys that contain
     * the corresponding (formatted) values. The `datatype` is either 'string', 'int' or 'float' as 
     * a string or a list of allowed values.
     */
    TagGroup measurement_variables;

    /**
     * The label that displays the error messages if there are some.
     */
    TagGroup error_display;

    /**
     * The `TagGroup` of inputboxes for the start values, the unique_id of the measurement variable 
     * is the key, the value is the inputbox.
     */
    TagGroup start_value_inputboxes;
    
    /**
     * The list of inputs for the series variable selects.
     */
    TagGroup series_selectboxes;
    
    /**
     * The list of labels showing the limits.
     */
    TagGroup limit_displays;
    
    /**
     * The list of inputs for the start value.
     */
    TagGroup start_inputboxes;
    
    /**
     * The list of inputs for the step width value.
     */
    TagGroup step_inputboxes;
    
    /**
     * The list of inputs for the end value.
     */
    TagGroup end_inputboxes;
    
    /**
     * The list of the labels display the "on each point" text.
     */
    TagGroup on_each_labels;
    
    /**
     * The `configuration` as a `TagGroup`, each key is the group, the value is another TagGroup 
     * with the keys and the 'value', 'datatype', 'default_value', 'ask_if_not_present', 
     * 'description' and 'restart_required' keys.
     */
    TagGroup configuration;

    /**
     * All inputs in a `TagList`
     */
    TagGroup config_inputs;

    /**
     * The values to ask
     */
    TagGroup ask_for_values;

    /**
     * The input boxes
     */
    TagGroup ask_for_inputs;

    /**
     * The message to show in the ask for dialog
     */
    string ask_vals_message;

    /**
     * The panels for the series settings and the configuration settings.
     */
    TagGroup panel_list;

    /**
     * Whether the user is allowed to switch between the series and the settings panel.
     */
    number allow_panel_change;

    /**
     * The mode, this can be "configuration", "series" or "ask_for"
     */
    string display_mode;

    /**
     * The map to get which file path button sets which input field, identifier of the button is 
     * the key, the value is the input dialog TagGroup.
     */
    TagGroup path_button_input_map;

    /**
     * Returns the measurement variable of the given `index`.
     *
     * @param index
     *      The index
     *
     * @return
     *      The measurement variable TagGroup
     */
    TagGroup _getMeasurementVariableByIndex(object self, number index){
        TagGroup tg;
        measurement_variables.TagGroupGetIndexedTagAsTagGroup(index, tg);

        return tg;
    }

    /**
     * Returns the measurement variable of the given `unique_id`.
     *
     * @param unique_id
     *      The id
     *
     * @return
     *      The measurement variable TagGroup
     */
    TagGroup _getMeasurementVariableById(object self, string unique_id){
        TagGroup tg;
        
        for(number i = 0; i < measurement_variables.TagGroupCountTags(); i++){
            tg = self._getMeasurementVariableByIndex(i);
            String id;
            tg.TagGroupGetTagAsString("unique_id", id);

            if(id == unique_id){
                return tg;
            }
        }

        TagGroup e;
        return e;
    }

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
     * Convert the user input `value` in the `measurement_variable`s format to a numeric value.
     *
     * @param measurement_variable
     *      The measurement variable that defines the format
     * @param value
     *      The string value
     * @param parsable
     *      Whether the `value` was parsable or not
     *
     * @return
     *      The numeric value to calculate with
     */
    number getNumericValue(object self, TagGroup measurement_variable, string value, number &parsable){
        string format = "";
        
        if(measurement_variable.TagGroupDoesTagExist("format")){
            measurement_variable.TagGroupGetTagAsString("format", format)
        }

        // trim() is defined in pylolib.s and is required automatically from python side
        value = value.trim();

        if(format == "hex"){
            // hex2dec() is defined in pylolib.s and is required automatically from python side
            return hex2dec(value, parsable);
        }
        else{
            // is_numeric() is defined in pylolib.s and is required automatically from python side
            parsable = is_numeric(value);
            return value.val();
        }
    }

    /**
     * Get the row index for the `identifier`.
     *
     * The row index is taken from extracting and parsing the number behind the last "-" in the 
     * `identifier`.
     *
     * @param identifier
     *      The identifier
     *
     * @return 
     *      The row index or -1 if not found
     */
    number getIdentifierIndex(object self, string identifier){
        number p = -1;

        // extract the row number
        while(identifier.find("-") >= 0){
            p = identifier.find("-");
            identifier = identifier.right(identifier.len() - p - 1);
        }
        
        // is_numeric() is defined in pylolib.s and is required automatically from python side
        if(is_numeric(identifier)){
            // convert to a number
            number index = identifier.val();
            return index;
        }

        return -1;
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
    number parseConfigIdentifier(object self, string identifier, string &group, string &key, number &index){
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
     * Get the label for this measurement variable. This contains the name and the unit if there 
     * is a unit.
     *
     * @param measurement_variable
     *      The measurement variable as a `TagGroup`
     *
     * @return
     *      The label
     */
    string _getMeasurementVariableLabel(object self, TagGroup measurement_variable){
        string label;
        string unit;

        measurement_variable.TagGroupGetTagAsString("name", label);
        measurement_variable.TagGroupGetTagAsString("unit", unit);
        if(unit != ""){
            label += " [" + unit + "]";
        }

        return label;
    }

    /**
     * Get the limit text for this measurement variable. 
     *
     * @param measurement_variable
     *      The measurement variable as a `TagGroup`
     *
     * @return
     *      The formatted limits
     */
    string _getMeasurementVariableLimits(object self, TagGroup measurement_variable){
        string min_value = "";
        string max_value = "";
        
        if(measurement_variable.TagGroupDoesTagExist("formatted_min_value")){
            measurement_variable.TagGroupGetTagAsString("formatted_min_value", min_value);
        }
        if(measurement_variable.TagGroupDoesTagExist("formatted_max_value")){
            measurement_variable.TagGroupGetTagAsString("formatted_max_value", max_value);
        }
        
        if(min_value == ""){
            measurement_variable.TagGroupGetTagAsString("min_value", min_value);
        }
        if(max_value == ""){
            measurement_variable.TagGroupGetTagAsString("max_value", max_value);
        }

        string limits = "";
        if(min_value != "" && max_value != ""){
            limits += min_value + ".." + max_value;
        }
        else if(min_value != ""){
            limits += ">= " + min_value;
            // limits += "= " + min_value;
        }
        else if(max_value != ""){
            limits += "<= " + max_value;
            // limits += "= " + max_value;
        }

        if(limits != ""){
            limits = "[" + limits + "]";
        }

        return limits;
    }

    /**
     * Get the measurement variable that the `series_select` has selected.
     *
     * @param series_select
     *      The select box
     *
     * @return
     *      The measurement variable that is selected or an invalid `TagGroup` if there is no 
     *      variable selected
     */
    TagGroup getSeriesSelectedMeasurementVariable(object self, TagGroup series_select){
        // get the index
        number selected_index = series_select.DLGGetValue();

        // get all items
        TagGroup items;
        series_select.TagGroupGetTagAsTagGroup("Items", items);

        // get selected item
        TagGroup item;
        items.TagGroupGetIndexedTagAsTagGroup(selected_index, item);

        // get the corresponding label
        string selected_label;
        item.TagGroupGetTagAsString("Label", selected_label);

        // find the selected measurement variable, the index is not turstworthy (because the 
        // indices change depending on the parent selectboxes) and there is no value so use the 
        // label to check
        TagGroup var;
        number found = 0;
        for(number i = 0; i < measurement_variables.TagGroupCountTags(); i++){
            var = self._getMeasurementVariableByIndex(i);
            string label = self._getMeasurementVariableLabel(var);

            if(label == selected_label){
                found = 1;
                break;
            }
        }

        if(found == 0){
            TagGroup d;
            return d;
        }
        else{
            return var;
        }
    }

    /**
     * Get the measurement variable that the series select in the `rowindex` has selected.
     *
     * @param rowindex
     *      The index of the roe
     *
     * @return
     *      The measurement variable that is selected or an invalid `TagGroup` if there is no 
     *      variable selected
     */
    TagGroup getSeriesSelectedMeasurementVariable(object self, number rowindex){
        // get the series select box of this row
        TagGroup series_select;
        series_selectboxes.TagGroupGetIndexedTagAsTagGroup(rowindex, series_select);

        // execute the DMViewDialog::getSeriesSelectedMeasurementVariable() function with the 
        // select box
        if(series_select.TagGroupIsValid()){
            return self.getSeriesSelectedMeasurementVariable(series_select);
        }
        else{
            TagGroup d;
            return d;
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
    number _validateMeasurementVariableValueInput(object self, string type, TagGroup input, string &errors){
        number valid = 1;
        TagGroup var;
        number index = -1;
        if(type == "start_value"){
            // remove "start_value-" from the identifier, the remaining part is the unique_id of the
            // measurement variable
            string unique_id;
            string identifier;
            input.DLGGetIdentifier(identifier);
            // "start_value-".len() == 12
            unique_id = identifier.right(identifier.len() - 12);
            var = self._getMeasurementVariableById(unique_id);
        }
        else if(type == "series_start" || type == "series_step_width" || type == "series_end"){
            // get the row index from the identifier
            string identifier;
            input.DLGGetIdentifier(identifier);
            index = self.getIdentifierIndex(identifier);

            if(index >= 0){
                // get the selected measurement variable from the index
                var = self.getSeriesSelectedMeasurementVariable(index);
            }
        }

        if(var.TagGroupIsValid()){
            string var_name;
            string input_name;
            string min_value;
            string max_value;
            string formatted_min_value;
            string formatted_max_value;
            number min_value_num;
            number max_value_num;
            number is_step_width = 0;
            number check_series_start = 0;
            number check_series_end = 0;
            var.TagGroupGetTagAsString("min_value", min_value);
            var.TagGroupGetTagAsString("max_value", max_value);
            var.TagGroupGetTagAsString("name", var_name);

            if(var.TagGroupDoesTagExist("formatted_min_value")){
                var.TagGroupGetTagAsString("formatted_min_value", formatted_min_value);
            }
            else{
                formatted_min_value = min_value;
            }
            if(var.TagGroupDoesTagExist("formatted_max_value")){
                var.TagGroupGetTagAsString("formatted_max_value", formatted_max_value);
            }
            else{
                formatted_max_value = max_value;
            }

            if(type == "start_value"){
                input_name = "start value";
            }
            else if(type == "series_start"){
                check_series_end = 1;
                input_name = "series start value"
            }
            else if(type == "series_step_width"){
                is_step_width = 1;
                input_name = "series step width"
            }
            else if(type == "series_end"){
                check_series_start = 1;
                input_name = "series end value"
            }

            string error_start_template = "The " + input_name + " for the " + var_name;
            errors = "";

            string value = input.DLGGetStringValue();
            if(value == ""){
                // value has to be given, no optional values are present and if there is a variable
                // the current input is enabled too
                errors += error_start_template + " is empty but it has to be given.\n";
                valid = 0;
            }
            else{
                number parsable;
                number value_num = self.getNumericValue(var, value, parsable);

                if(parsable == 0){
                    errors += error_start_template + " not parsable.\n";
                    valid = 0;
                }
                else{
                    string start_value;
                    string end_value;
                    number start_num;
                    number end_num;

                    if(index >= 0 && (is_step_width == 1 || check_series_start == 1)){
                        // get the start input of this row
                        TagGroup start_input;
                        start_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, start_input);

                        // get value and convert to number
                        start_value = start_input.DLGGetStringValue();

                        if(start_value != ""){
                            number start_parsable;
                            start_num = self.getNumericValue(var, start_value, start_parsable);

                            if(start_parsable == 0){
                                start_value = "";
                                start_num = 0;
                            }
                        }
                    }
                    if(index >= 0 && (is_step_width == 1 || check_series_end == 1)){
                        // get the end input of this row
                        TagGroup end_input;
                        end_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, end_input);

                        // get value and convert to number
                        end_value = end_input.DLGGetStringValue();

                        if(end_value != ""){
                            number end_parsable;
                            end_num = self.getNumericValue(var, end_value, end_parsable);

                            if(end_parsable == 0){
                                end_value = "";
                                end_num = 0;
                            }
                        }
                    }

                    if(is_step_width){
                        if(value_num <= 0){
                            errors += error_start_template + " is less or equal to 0 which is not allowed (" + value_num + "<=0).\n";
                            valid = 0;
                        }
                        if(start_value != "" && end_value != "" && value_num > end_num - start_num){
                            errors += error_start_template + " greater than the difference between the start and end value, so there is only the start value in the series (the next step is outside the end already) (" + value_num + ">" + (end_num - start_num) + ").\n";
                            valid = 0;
                        }
                    }
                    else{
                        if(min_value != ""){
                            min_value_num = min_value.val();

                            if(value_num < min_value_num){
                                errors += error_start_template + " is less than the minimum value (" + value_num + "<" + min_value_num + ").\n";
                                valid = 0;
                            }
                        }
                        if(max_value != ""){
                            max_value_num = max_value.val();

                            if(value_num > max_value_num){
                                errors += error_start_template + " is greater than the maximum value (" + value_num + ">" + max_value_num + ").\n";
                                valid = 0;
                            }
                        }

                        if(check_series_start && value_num <= start_num){
                            errors += error_start_template + " is less or equal to the start value (" + value_num + "<=" + start_num + ").\n"
                            valid = 0;
                        }
                        if(check_series_end && value_num >= end_num){
                            errors += error_start_template + " is greater or equal to the end value (" + value_num + ">=" + end_num + ").\n"
                            valid = 0;
                        }
                    }
                }
            }
        }

        return valid;
    }

    /**
     * Validates all inputs.
     */
    number validateInputs(object self, string &errors){
        number valid = 1;
        errors = "";

        for(number j = 0; j < measurement_variables.TagGroupCountTags(); j++){
            TagGroup input;
            string input_error = "";

            // validate start input
            TagGroup var = self._getMeasurementVariableByIndex(j);
            string unique_id;
            var.TagGroupGetTagAsString("unique_id", unique_id);

            start_value_inputboxes.TagGroupGetTagAsTagGroup(unique_id, input);

            input_error = "";
            valid = valid && self._validateMeasurementVariableValueInput("start_value", input, input_error);
            errors += input_error;

            // validate row, there is one row for each measurement variable so it is the same 
            // counter

            // start
            start_inputboxes.TagGroupGetIndexedTagAsTagGroup(j, input);
            input_error = ""
            valid = valid && self._validateMeasurementVariableValueInput("series_start", input, input_error);
            errors += input_error;

            // step
            step_inputboxes.TagGroupGetIndexedTagAsTagGroup(j, input);
            input_error = ""
            valid = valid && self._validateMeasurementVariableValueInput("series_step_width", input, input_error);
            errors += input_error;

            // end
            end_inputboxes.TagGroupGetIndexedTagAsTagGroup(j, input);
            input_error = ""
            valid = valid && self._validateMeasurementVariableValueInput("series_end", input, input_error);
            errors += input_error;
        }

        return valid;
    }

    /**
     * The callback when a dir path button is clicked.
     */
    void selectPathCallback(object self){
        for(number i = 0; i < path_button_input_map.TagGroupCountTags(); i++){
            string button_identifier = path_button_input_map.TagGroupGetTagLabel(i);

            TagGroup button = self.lookupElement(button_identifier);

            if(button.TagGroupIsValid()){
                if(button.DLGGetValue() == 1){
                    // this button is clicked

                    // remove clicked status
                    button.DLGValue(0);

                    // the type
                    string type = button.DLGGetTitle();

                    // get the input and the corresponding start value
                    TagGroup input;
                    string start_path = "";
                    if(path_button_input_map.TagGroupGetTagAsTagGroup(button_identifier, input)){
                        start_path = input.DLGGetStringValue();
                    }

                    // input is empty
                    if(start_path == ""){
                        start_path = GetApplicationDirectory(0, 1);

                        if(type == "filepath"){
                            start_path = start_path.PathConcatenate("file.dat");
                        }
                    }
                    
                    // show the dialog
                    string target_path;
                    number success;

                    if(type == "dirpath"){
                        success = GetDirectoryDialog(self.getFrameWindow(), "Select a directory", "Select a directory", start_path, target_path);
                    }
                    else{
                        success = SaveAsDialog(self.getFrameWindow(), "Save as", start_path, target_path);
                    }

                    if(success && input.TagGroupIsValid()){
                        input.DLGValue(target_path);
                    }
                }
            }
        }
    }

    /**
     * The callback for the start input.
     */
    void startChangedCallback(object self, TagGroup series_end_input){
        string errors;
        self._validateMeasurementVariableValueInput("start_value", series_end_input, errors);
        error_display.DLGTitle(errors);
    }

    /**
     * The callback for the series start input.
     *
     * This changes the start values to the value of the series start.
     */
    void seriesStartChangedCallback(object self, TagGroup series_start_input){
        string errors;
        self._validateMeasurementVariableValueInput("series_start", series_start_input, errors);
        error_display.DLGTitle(errors);

        // get the identifier
        string identifier;
        series_start_input.DLGGetIdentifier(identifier);
        
        // get the row index from the identifier
        number index = self.getIdentifierIndex(identifier);
        // get the selected measurement variable from the row index
        TagGroup var = self.getSeriesSelectedMeasurementVariable(index);

        if(var.TagGroupIsValid()){
            // the start changes if the DMViewDialog::seriesSelectChanged() changes it to "" because
            // the measurement variable is unselected, then the var is not a valid TagGroup
            string unique_id;
            var.TagGroupGetTagAsString("unique_id", unique_id);

            TagGroup start_input;
            start_value_inputboxes.TagGroupGetTagAsTagGroup(unique_id, start_input);

            start_input.DLGValue(series_start_input.DLGGetStringValue());
        }
    }

    /**
     * The callback for the series step width input.
     */
    void seriesStepWidthChangedCallback(object self, TagGroup series_step_width_input){
        string errors;
        self._validateMeasurementVariableValueInput("series_step_width", series_step_width_input, errors);
        error_display.DLGTitle(errors);
    }

    /**
     * The callback for the series end input.
     */
    void seriesEndChangedCallback(object self, TagGroup series_end_input){
        string errors;
        self._validateMeasurementVariableValueInput("series_end", series_end_input, errors);
        error_display.DLGTitle(errors);
    }

    /**
     * The callback for the series select.
     *
     * This enables or disables all other inputs in the same row. Elements are enabled if a 
     * measurement variable is selected, disabled otherwise. If the elements are disabled, their 
     * value will be set to "". 
     *
     * The next series select box will be disabled if the current one does not contain a measurement
     * variable. Note that this function will be called recursively on all following selectboxes.
     * This is necessary for disabling the rows if one of the parent select boxes deletes the
     * measurement variable.
     */
    void seriesSelectChanged(object self, TagGroup series_select){
        // get the index of the row
        string identifier;
        series_select.DLGGetIdentifier(identifier);
        number index = self.getIdentifierIndex(identifier);

        // get the selected measurement variable
        TagGroup var = self.getSeriesSelectedMeasurementVariable(series_select);

        if(var.TagGroupIsValid()){
            // show the limits
            TagGroup limit_display;
            limit_displays.TagGroupGetIndexedTagAsTagGroup(index, limit_display);
            limit_display.DLGTitle(self._getMeasurementVariableLimits(var));

            // enable the start value
            string start = "";
            if(var.TagGroupDoesTagExist("formatted_start")){
                var.TagGroupGetTagAsString("formatted_start", start);
            }
            if(start == ""){
                var.TagGroupGetTagAsString("start", start);
            }
            TagGroup start_input;
            start_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, start_input);
            start_input.DLGValue(start);
            start_input.DLGEnabled(1);
            if(self.isShown()){
                // DLGEnabled() does not work if the dialog is shown already
                string i;
                start_input.DLGGetIdentifier(i);
                self.setElementIsEnabled(i, 1);
            }

            // enable the step width value
            string step = "";
            if(var.TagGroupDoesTagExist("formatted_step")){
                var.TagGroupGetTagAsString("formatted_step", step);
            }
            if(step == ""){
                var.TagGroupGetTagAsString("step", step);
            }
            TagGroup step_input;
            step_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, step_input);
            step_input.DLGValue(step);
            step_input.DLGEnabled(1);
            if(self.isShown()){
                // DLGEnabled() does not work if the dialog is shown already
                string i;
                step_input.DLGGetIdentifier(i);
                self.setElementIsEnabled(i, 1);
            }

            // enable the end value
            string end = "";
            if(var.TagGroupDoesTagExist("formatted_end")){
                var.TagGroupGetTagAsString("formatted_end", end);
            }
            if(end == ""){
                var.TagGroupGetTagAsString("end", end);
            }
            TagGroup end_input;
            end_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, end_input);
            end_input.DLGValue(end);
            end_input.DLGEnabled(1);
            if(self.isShown()){
                // DLGEnabled() does not work if the dialog is shown already
                string i;
                end_input.DLGGetIdentifier(i);
                self.setElementIsEnabled(i, 1);
            }
        }
        else{
            // hide the limits
            TagGroup limit_display;
            limit_displays.TagGroupGetIndexedTagAsTagGroup(index, limit_display);
            limit_display.DLGTitle("");

            // disable the start value
            TagGroup start_input;
            start_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, start_input);
            start_input.DLGValue("");
            start_input.DLGEnabled(0);
            if(self.isShown()){
                // DLGEnabled() does not work if the dialog is shown already
                string i;
                start_input.DLGGetIdentifier(i);
                self.setElementIsEnabled(i, 0);
            }

            // disable the step width value
            TagGroup step_input;
            step_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, step_input);
            step_input.DLGValue("");
            step_input.DLGEnabled(0);
            if(self.isShown()){
                // DLGEnabled() does not work if the dialog is shown already
                string i;
                step_input.DLGGetIdentifier(i);
                self.setElementIsEnabled(i, 0);
            }

            // disable the end value
            TagGroup end_input;
            end_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, end_input);
            end_input.DLGValue("");
            end_input.DLGEnabled(0);
            if(self.isShown()){
                // DLGEnabled() does not work if the dialog is shown already
                string i;
                end_input.DLGGetIdentifier(i);
                self.setElementIsEnabled(i, 0);
            }
        }

        // enable/disable the next series select box if it exists
        if(index + 1 < series_selectboxes.TagGroupCountTags()){
            string name;
            number enabled;
            number update_next_row = 0;
            if(var.TagGroupIsValid()){
                var.TagGroupGetTagAsString("name", name);
                enabled = 1;
            }
            else{
                name = "--";
                enabled = 0;
            }

            // update the "On each ..."-text
            TagGroup on_each_label;
            on_each_labels.TagGroupGetIndexedTagAsTagGroup(index, on_each_label);
            on_each_label.DLGTitle("On each " + name + " point series over...");

            TagGroup next_series_select;
            series_selectboxes.TagGroupGetIndexedTagAsTagGroup(index + 1, next_series_select);
            next_series_select.DLGEnabled(enabled);
            if(self.isShown()){
                // DLGEnabled() does not work if the dialog is shown already
                string i;
                next_series_select.DLGGetIdentifier(i);
                self.setElementIsEnabled(i, enabled);
            }
            if(enabled == 0){
                if(next_series_select.DLGGetValue() != 0){
                    // next row had a measurement variable selected, now not anymore, handle the 
                    // updates
                    update_next_row = 1;
                }
                // unselect the measurement variable, this will 
                next_series_select.DLGValue(0);
            }
            else if(next_series_select.DLGGetValue() != 0){
                // there was a measurement variable selected but the items are changed, if the 
                // current select box does a series over the measurement variable selected in the 
                // next_series_select, the measurement variable item will be removed from the 
                // next_series_select, this means the selected index has a different meaning then 
                // which needs to update the limits and start/end values again
                update_next_row = 1;
            }

            // clear all items
            TagGroup items;
            next_series_select.TagGroupGetTagAsTagGroup("Items", items);
            items.TagGroupDeleteAllTags();

            // add the "no series" option as option 0
            next_series_select.DLGAddChoiceItemEntry("--");

            // add all remaining measurement variables
            for(number j = 0; j < measurement_variables.TagGroupCountTags(); j++){
                // the variable to add
                TagGroup add_var = self._getMeasurementVariableByIndex(j);

                string add_id;
                add_var.TagGroupGetTagAsString("unique_id", add_id);

                // check if the variable is set in one of the parents already
                number var_selected_in_parent = 0;
                for(number k = 0; k <= index; k++){
                    TagGroup parent_series_select;
                    series_selectboxes.TagGroupGetIndexedTagAsTagGroup(k, parent_series_select);

                    TagGroup parent_var = self.getSeriesSelectedMeasurementVariable(parent_series_select);

                    if(parent_var.TagGroupIsValid()){
                        string parent_id;
                        parent_var.TagGroupGetTagAsString("unique_id", parent_id);

                        if(parent_id == add_id){
                            // this parent contains this variable already
                            var_selected_in_parent = 1;
                            break;
                        }
                    }
                }

                if(var_selected_in_parent == 0){
                    // only add if the parent does not contain the variable
                    next_series_select.DLGAddChoiceItemEntry(self._getMeasurementVariableLabel(add_var))
                }
            }

            if(update_next_row){
                // update the next row too
                self.seriesSelectChanged(next_series_select);
            }
        }
    }

    /**
     * Switch the panels to show the series panel.
     */
    void switchToSeriesPanel(object self){
        panel_list.DLGValue(0);
    }

    /**
     * Switch the panels to show the configuration panel.
     */
    void switchToConfigurationPanel(object self){
        panel_list.DLGValue(1);
    }

    /**
     * Create one row for the lower wrapper.
     *
     * @param columns
     *      The number of columns to use in that row
     *
     * @return 
     *      The line as a dialog group
     */
    TagGroup _createInputLine(object self, number columns){
        TagGroup input_line = DLGCreateGroup();
        input_line.DLGTableLayout(columns, 1, 0);
        input_line.DLGExpand("X");
        input_line.DLGFill("X");

        return input_line;
    }

    /**
     * Create the content for the series panel.
     *
     * @return
     *      The series content as a dialog group
     */
    TagGroup _createSeriesSetupContent(object self){
        TagGroup wrapper = DLGCreateGroup();

        TagGroup description_line = DLGCreateGroup();
        // description_line.DLGTableLayout(2, 1, 0);
        description_line.DLGExpand("X");
        description_line.DLGFill("X");

        // description text
        string description = "Create a new measurememt series to measure probes in the lorentz mode ";
        description += "(low mag mode). Select the start properties. The series defines over which ";
        description += "variables the series will be done. On each series point there can be ";
        description += "another series.\n"
        // description += "\n";
        description += "The 'start' value of the 'series' definition will always overwrite the ";
        description += "'start' definition. The 'step-width' will be added as many times to the ";
        description += "series 'start' value as it is less or equal to the 'end'. This means that ";
        description += "the end value will not be reached necessarily (when 'step-width' is not a ";
        description += "divider of 'end'-'start').";
        TagGroup description_label = DLGCreateLabel(description, 135);
        description_label.DLGHeight(5);
        description_label.DLGAnchor("West");
        description_line.DLGAddElement(description_label);

        // change to measurement button
        // TagGroup settings_button = DLGCreatePushButton("Settings", "switchToConfigurationPanel");
        // settings_button.DLGAnchor("East");
        // description_line.DLGAddElement(settings_button);

        wrapper.DLGAddElement(description_line);

        // TagGroup error_headline = DLGCreateLabel("Errors:");
        // wrapper.DLGAddElement(error_headline);
        TagGroup error_box = DLGCreateBox("Errors");

        error_display = DLGCreateLabel("Currently no errors", 135);
        error_display.DLGHeight(2);
        error_display.DLGExpand("X");
        error_display.DLGFill("X");
        // wrapper.DLGAddElement(error_display);
        error_box.DLGAddElement(error_display);
        wrapper.DLGAddElement(error_box);

        // the number of variables to show in one row
        number max_cols = 2;
        number max_rows = ceil(measurement_variables.TagGroupCountTags() / max_cols);

        // TagGroup upper_wrapper = DLGCreateBox("Start parameters");
        TagGroup upper_wrapper = DLGCreateGroup();
        upper_wrapper.DLGTableLayout(max_cols, 1, 0);
        upper_wrapper.DLGExpand("X");
        upper_wrapper.DLGFill("X");

        for(number i = 0; i < max_cols; i++){
            TagGroup col = DLGCreateBox("Start parameters");
            col.DLGTableLayout(3, max_rows, 0);
            col.DLGExpand("X");
            col.DLGFill("X");
            
            // go through the measurement variables and add all the start input boxes
            for(number j = i * max_rows; j < min((i + 1) * max_rows, measurement_variables.TagGroupCountTags()); j++){
                TagGroup var = self._getMeasurementVariableByIndex(j);

                string unique_id;
                var.TagGroupGetTagAsString("unique_id", unique_id);

                string label = self._getMeasurementVariableLabel(var);
                string limits = self._getMeasurementVariableLimits(var);

                TagGroup label_element = DLGCreateLabel(label, 28);
                label_element.DLGAnchor("East");
                col.DLGAddElement(label_element);
                
                string start = "";
                if(var.TagGroupDoesTagExist("formatted_start")){
                    var.TagGroupGetTagAsString("formatted_start", start);
                }
                if(start == ""){
                    var.TagGroupGetTagAsString("start", start);
                }

                TagGroup start_input = DLGCreateStringField(start, 12, "startChangedCallback");
                start_input.DLGAnchor("West");
                start_input.DLGIdentifier("start_value-" + unique_id);

                // add the input box to the internal list to access them later on
                number index = start_value_inputboxes.TagGroupCreateNewLabeledTag(unique_id);
                start_value_inputboxes.TagGroupSetIndexedTagAsTagGroup(index, start_input);
                
                // add the limits
                col.DLGAddElement(DLGCreateLabel(limits, 16));
                // // add the start
                col.DLGAddElement(start_input);
            }
            upper_wrapper.DLGAddElement(col);
        }

        wrapper.DLGAddElement(upper_wrapper);

        // prepare the series paramter inputs
        TagGroup lower_wrapper = DLGCreateBox("Series parameters");

        // number of input rows
        number c = measurement_variables.TagGroupCountTags();

        // column widths
        number cw2 = 14;
        number cw3 = 12;
        number cw4 = 12;
        number cw5 = 12;
        
        // header
        TagGroup input_line = self._createInputLine(4);
        input_line.DLGAddElement(DLGCreateLabel("Series over...", 54));
        input_line.DLGAddElement(DLGCreateLabel("Start", cw3));
        input_line.DLGAddElement(DLGCreateLabel("Step width", cw4));
        input_line.DLGAddElement(DLGCreateLabel("End", cw5));

        lower_wrapper.DLGAddElement(input_line);
        lower_wrapper.DLGExpand("X");
        lower_wrapper.DLGFill("X");

        // add measurement variable rows
        for(number i = 0; i < c ; i++){
            TagGroup input_line = self._createInputLine(5);
            TagGroup series_select = DLGCreateChoice(0, "seriesSelectChanged");
            // padding has to be negative, don't know why, otherwise it is in the wrong direction,
            // also setting padding for right value does the wrong outcome
            series_select.DLGExternalPadding(0, i * -50, 0, 0);
            series_select.DLGWidth(190);
            series_select.DLGAnchor("West");
            series_select.DLGSide("Left");
            if(i > 0){
                // enable only the first select box by default
                series_select.DLGEnabled(0);
                series_select.DLGAddChoiceItemEntry("--");
            }
            else{
                // add all measurement variables to the first select box
                for(number j = 0; j < measurement_variables.TagGroupCountTags(); j++){
                    TagGroup var = self._getMeasurementVariableByIndex(j);
                    series_select.DLGAddChoiceItemEntry(self._getMeasurementVariableLabel(var))
                }
            }
            series_select.DLGIdentifier("series_variable-" + i);
            series_selectboxes.TagGroupInsertTagAsTagGroup(infinity(), series_select);
            input_line.DLGAddElement(series_select);

            // add the (empty) limit display, value will be updated by 
            // DMViewDialog::seriesSelectChanged()
            TagGroup limit_display = DLGCreateLabel("", cw2);
            limit_displays.TagGroupInsertTagAsTagGroup(infinity(), limit_display);
            input_line.DLGAddElement(limit_display);

            // add the start input, value will be updated by DMViewDialog::seriesSelectChanged()
            TagGroup start_input = DLGCreateStringField("", cw3, "seriesStartChangedCallback");
            start_input.DLGIdentifier("series_start-" + i);
            start_inputboxes.TagGroupInsertTagAsTagGroup(infinity(), start_input);
            input_line.DLGAddElement(start_input);

            // add the step width input, value will be updated by DMViewDialog::seriesSelectChanged()
            TagGroup step_input = DLGCreateStringField("", cw4, "seriesStepWidthChangedCallback");
            step_input.DLGIdentifier("series_step-" + i);
            step_inputboxes.TagGroupInsertTagAsTagGroup(infinity(), step_input);
            input_line.DLGAddElement(step_input);

            // add the end input, value will be updated by DMViewDialog::seriesSelectChanged()
            TagGroup end_input = DLGCreateStringField("", cw5, "seriesEndChangedCallback");
            end_input.DLGIdentifier("series_end-" + i);
            end_inputboxes.TagGroupInsertTagAsTagGroup(infinity(), end_input);
            input_line.DLGAddElement(end_input);

            lower_wrapper.DLGAddElement(input_line);
            
            // add the "on each point"-label, between the measurement variables, text will be 
            // updated by DMViewDialog::seriesSelectChanged()
            if(i + 1 < c){
                TagGroup on_each_label = DLGCreateLabel("", 80);
                on_each_label.DLGIdentifier("on_each_label-" + i);
                on_each_label.DLGExternalPadding(0, (i + 1) * -50, 0, 0);
                on_each_label.DLGAnchor("West");
                on_each_label.DLGExpand("X");
                on_each_label.DLGHeight(1);
                on_each_labels.TagGroupInsertTagAsTagGroup(infinity(), on_each_label);
                lower_wrapper.DLGAddElement(on_each_label);
            }
        }

        // trigger changes for all selectboxes, otherwise the text of the "on ech point"-labels 
        // cannot be changed on runtime, also this enables and disables all inputs, ect.
        for(number j = 0; j < series_selectboxes.TagGroupCountTags(); j++){
            TagGroup series_select;
            series_selectboxes.TagGroupGetIndexedTagAsTagGroup(j, series_select);
            self.seriesSelectChanged(series_select);
        }

        wrapper.DLGAddElement(lower_wrapper);

        return wrapper;
    }

    /**
    * Create an input line for a dialog. The line contains the label, the input and the description.
    *
    * @param value_definition
    *      A `TagGroup` that defines the value input line
    * @param input
    *      The reference to save the input field to
    *
    * @return 
    *      The dialog group that represents the input line
    */
    TagGroup createValueInputLine(object self, TagGroup value_definition, TagGroup &input){
        // column widths
        number cw1 = 20; // label column
        number cw2 = 40; // value column
        number cw3 = 60; // description column

        string description;
        string type;
        string name;
        value_definition.TagGroupGetTagAsString("description", description);
        value_definition.TagGroupGetTagAsString("datatype", type);
        value_definition.TagGroupGetTagAsString("name", name);

        number restart_required = 0;
        if(value_definition.TagGroupDoesTagExist("restart_required")){
            value_definition.TagGroupGetTagAsBoolean("restart_required", restart_required);
        }

        if(restart_required){
            name += "*"
        }

        TagGroup value_wrapper = DLGCreateGroup();

        TagGroup line = DLGCreateGroup();
        line.DLGTableLayout(3, 1, 0);
        line.DLGExpand("X");
        line.DLGAnchor("East");
        line.DLGFill("X");

        if(type != "boolean"){
            TagGroup label = DLGCreateLabel(name, cw1);
            label.DLGAnchor("North");
            line.DLGAddElement(label);
        }

        if(type == "int"){
            number value;
            value_definition.TagGroupGetTagAsLong("value", value);
            input = DLGCreateIntegerField(round(value), cw2);
        }
        else if(type == "float"){
            number value;
            value_definition.TagGroupGetTagAsFloat("value", value);
            input = DLGCreateRealField(value, cw2, 4);
        }
        else if(type == "boolean"){
            number value;
            value_definition.TagGroupGetTagAsBoolean("value", value);
            input = DLGCreateCheckBox(name, value != 0 ? 1 : 0);
            input.DLGAnchor("East");

            TagGroup inner_line_wrapper = DLGCreateGroup();
            // inner_line_wrapper.DLGWidth(cw1 + cw2);
            inner_line_wrapper.DLGAddElement(input);
            inner_line_wrapper.DLGAnchor("East");
            inner_line_wrapper.DLGSide("Right");
            line.DLGAddElement(inner_line_wrapper);
        }
        else if(type == "dirpath" || type == "filepath"){
            string value;
            value_definition.TagGroupGetTagAsString("value", value);

            TagGroup inner_line_wrapper = DLGCreateGroup();
            inner_line_wrapper.DLGTableLayout(2, 1, 0);

            input = DLGCreateStringField(value, cw2 - 5);
            input.DLGAnchor("West");
            input.DLGSide("Left");
            inner_line_wrapper.DLGAddElement(input);

            number s = 24;
            string icon_path = __file__.PathExtractDirectory(0).PathConcatenate("icons");
            if(type == "dirpath"){
                icon_path = icon_path.PathConcatenate("directory-icon-" + s + ".tiff")
            }
            else{
                icon_path = icon_path.PathConcatenate("file-icon-" + s + ".tiff")
            }
            rgbimage button_img := OpenImage(icon_path);

            String button_identifier = "path_button_" + path_button_input_map.TagGroupCountTags();
            TagGroup button = DLGCreateDualStateBevelButton(button_identifier, button_img, button_img, "selectPathCallback");
            button.DLGTitle(type);
            button.DLGIdentifier(button_identifier);
            button.DLGAnchor("East");
            button.DLGSide("Right");
            inner_line_wrapper.DLGAddElement(button);

            // save the link between the button and the input
            if(!path_button_input_map.TagGroupDoesTagExist(button_identifier)){
                path_button_input_map.TagGroupCreateNewLabeledTag(button_identifier);
            }
            path_button_input_map.TagGroupSetTagAsTagGroup(button_identifier, input);

            line.DLGAddElement(inner_line_wrapper);
        }
        else if(type == "options"){
            string value;
            number value_index;
            value_definition.TagGroupGetTagAsString("value", value);

            TagGroup options;
            value_definition.TagGroupGetTagAsTagGroup("options", options);

            input = DLGCreateChoice()
            for(number i = 0; i < options.TagGroupCountTags(); i++){
                string item_text;
                options.TagGroupGetIndexedTagAsString(i, item_text);

                input.DLGAddChoiceItemEntry(item_text);

                if(value == item_text){
                    value_index = i;
                }
            }

            input.DLGValue(value_index);
        }
        else{
            string value;
            value_definition.TagGroupGetTagAsString("value", value);
            input = DLGCreateStringField(value, cw2);
        }

        if(type != "boolean" && type != "dirpath" && type != "filepath"){
            input.DLGAnchor("North");
            line.DLGAddElement(input);
        }

        if(restart_required){
            description += " (Changing restarts program)"
        }
        TagGroup description_label = DLGCreateLabel(description, cw3);
        description_label.DLGHeight(ceil(description.len() / 55));
        description_label.DLGAnchor("East");
        line.DLGAddElement(description_label);

        value_wrapper.DLGAddElement(line);

        return value_wrapper;
    }

    /**
     * Create the content for the configuration panel.
     *
     * @return
     *      The configuration content as a dialog group
     */
    TagGroup _createConfigurationContent(object self){
        TagGroup wrapper = DLGCreateGroup();

        TagGroup description_line = DLGCreateGroup();
        // description_line.DLGTableLayout(2, 1, 0);
        description_line.DLGExpand("X");
        description_line.DLGFill("X");

        // description text
        string description = "Set the settings used for recording a new measurement."
        TagGroup description_label = DLGCreateLabel(description, 110);
        description_label.DLGHeight(1);
        description_label.DLGAnchor("West");
        description_line.DLGAddElement(description_label);

        // change to measurement button
        // TagGroup measurement_button = DLGCreatePushButton("Switch to series", "switchToSeriesPanel");
        // measurement_button.DLGAnchor("East");
        // description_line.DLGAddElement(measurement_button);

        wrapper.DLGAddElement(description_line);

        // TagGroup error_headline = DLGCreateLabel("Errors:");
        // wrapper.DLGAddElement(error_headline);
        // TagGroup error_box = DLGCreateBox("Errors");

        // error_display = DLGCreateLabel("Currently no errors", 130);
        // error_display.DLGHeight(2);
        // error_display.DLGExpand("X");
        // error_display.DLGFill("X");
        // // wrapper.DLGAddElement(error_display);
        // error_box.DLGAddElement(error_display);
        // wrapper.DLGAddElement(error_box);

        // the number of variables to show in one row
        number max_cols = 1;
        number max_rows = 4;

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
            if(page_counter > 0 && remaining_rows < group_rows && group_rows < max_rows && (remaining_rows < 3 || group_rows - remaining_rows < 3)){
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

                if(!value_settings.TagGroupDoesTagExist("name")){
                    value_settings.TagGroupCreateNewLabeledTag("name");
                    value_settings.TagGroupSetTagAsString("name", key);
                }

                TagGroup input;
                TagGroup value_wrapper = self.createValueInputLine(value_settings, input);

                input.DLGIdentifier(group + "/" + key + "/" + counter);
                config_inputs.TagGroupInsertTagAsTagGroup(infinity(), input);

                group_box.DLGAddElement(value_wrapper);
                counter++;

                row_counter++;

                if(row_counter > max_rows){
                    tab.DLGAddElement(group_box);

                    group_box = DLGCreateBox(group);
                    group_box.DLGExpand("X");
                    group_box.DLGFill("X");
                    group_box.DLGAnchor("West");
                    if(max_cols > 1){
                        group_box.DLGTableLayout(max_cols, min(group_rows, remaining_rows), 0);
                    }

                    row_counter = 0;
                    page_counter++;
                    tabs.DLGAddTab(tab);
                    tab = DLGCreateTab("Page " + (page_counter + 1));
                    tab.DLGExpand("X");
                    tab.DLGFill("X");
                    tab.DLGAnchor("West");
                }
            }

            if(row_counter > 0){
                tab.DLGAddElement(group_box);
            }
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

        TagGroup restart_required_text = DLGCreateLabel("*Changing this value will restart the program.");
        restart_required_text.DLGAnchor("West");
        restart_required_text.DLGExpand("X");
        restart_required_text.DLGFill("X");
        wrapper.DLGAddElement(restart_required_text);

        return wrapper;
    }

	/**
	 * Create the contents for the ask-for dialog. 
     *
     * @param msg
     *      The message to show
	 *
	 * @return
	 *		The dialogs contents as a TagGroup for initializing an
	 *		UIFrame
	 */
	TagGroup _createAskForContent(object self, string msg){
        TagGroup outer_wrapper = DLGCreateGroup();

        TagGroup label = DLGCreateLabel(msg, 130);
        label.DLGHeight(1);
        outer_wrapper.DLGAddElement(label);

        TagGroup wrapper = DLGCreateGroup();
        
        for(number i = 0; i < ask_for_values.TagGroupCountTags(); i++){
            TagGroup value_settings;
            ask_for_values.TagGroupGetIndexedTagAsTagGroup(i, value_settings);
            
            TagGroup input;
            TagGroup value_wrapper = self.createValueInputLine(value_settings, input);

            input.DLGIdentifier("ask_for_input-" + i);
            ask_for_inputs.TagGroupInsertTagAsTagGroup(i, input);

            wrapper.DLGAddElement(value_wrapper);
        }

        outer_wrapper.DLGAddElement(wrapper);

		return outer_wrapper;
    }

	/**
	 * Create the contents of the dialog. 
     *
     * @param title
     *      The title of the dialog
	 *
	 * @return
	 *		The dialogs contents as a TagGroup for initializing an
	 *		UIFrame
	 */
	TagGroup _createContent(object self, string title){
		TagGroup dialog_items;
		TagGroup dialog_tags = DLGCreateDialog(title, dialog_items);

        // the map for finding the input for the file path buttons
        path_button_input_map = NewTagGroup();

        // input boxes for the ask-for panel
        ask_for_inputs = NewTagList();

        // input boxes for the configuration panel
        config_inputs = NewTagList();

        // input boxes for the series panel
        series_selectboxes = NewTagList();
        limit_displays = NewTagList();
        start_inputboxes = NewTagList();
        step_inputboxes = NewTagList();
        end_inputboxes = NewTagList();
        on_each_labels = NewTagList();

        // input boxes for the series panel
        start_value_inputboxes = NewTagGroup();

        if(display_mode == "ask_for"){
            panel_list = DLGCreatePanelList();

            TagGroup ask_for_panel = DLGCreatePanel();
            ask_for_panel.DLGAddElement(self._createAskForContent(ask_vals_message));
            panel_list.DLGAddTab(ask_for_panel);
        }
        else{
            panel_list = DLGCreateTabList(0);

            TagGroup series_panel = DLGCreateTab("Create series");
            series_panel.DLGAddElement(self._createSeriesSetupContent());
            panel_list.DLGAddTab(series_panel);

            TagGroup configuration_panel = DLGCreateTab("Settings");
            configuration_panel.DLGAddElement(self._createConfigurationContent());
            panel_list.DLGAddTab(configuration_panel);
        }
        
        // Tabs do not work as a direct child of the dialog items, so probably panels don't too, 
        // therefore create a warpper 
        // https://stackoverflow.com/q/61477040/5934316
        TagGroup wrapper = DLGCreateGroup();
        wrapper.DLGExpand("XY");
        wrapper.DLGAddElement(panel_list);

        dialog_items.DLGAddElement(wrapper);

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
	object init(object self, string startup, string title, TagGroup measurement_vars, TagGroup configuration_vars, TagGroup ask_vals, String msg){
        measurement_variables = measurement_vars;
        configuration = configuration_vars;
        ask_for_values = ask_vals;
        display_mode = startup;
        ask_vals_message = msg
        allow_panel_change = 1;
		self.super.init(self._createContent(title));
        
		return self;
	}

    void updateAllowPanelChange(object self, number allow_change){
        allow_panel_change = allow_change;
        panel_list.DLGEnabled(allow_panel_change);
    }

    /**
     * Show the series dialog.
     */
    number poseSeries(object self){
        self.switchToSeriesPanel();
        self.updateAllowPanelChange(0);
        return self.pose();
    }

    /**
     * Show the configuration dialog.
     */
    number poseConfiguration(object self){
        self.switchToConfigurationPanel();
        self.updateAllowPanelChange(0);
        return self.pose();
    }

    /**
     * Overwriting pose function, before clicking 'OK' the inputs are validated. If there are errors
     * an error dialog is shown.
     */
    number pose(object self){
        if(self.super.pose()){
            string errors;
            if(self.validateInputs(errors) != 1){
                showAlert("There are the following errors in the current series: \n\n" + errors + "\n\nEither fix them or press 'Cancel'.", 0);
                error_display.DLGTitle(errors);
                return self.pose();
            }
            else{
                return 1;
            }
        }
        else{
            return 0;
        }
    }

    /**
     * Get the measurement start values as a `TagGroup`, the keys are the unique_ids of the 
     * measurement variables, the values are the (unformatted) values
     *
     * @return
     *      The measurement start values
     */
    TagGroup getStart(object self){
        TagGroup start = NewTagGroup();

        // travel through measurement variables and get the corresponding input, save the value 
        // (unformatted)
        for(number i = 0; i < measurement_variables.TagGroupCountTags(); i++){
            TagGroup var = self._getMeasurementVariableByIndex(i);
            string unique_id;
            var.TagGroupGetTagAsString("unique_id", unique_id);

            TagGroup input;
            start_value_inputboxes.TagGroupGetTagAsTagGroup(unique_id, input);

            string value = input.DLGGetStringValue();

            number index = start.TagGroupCreateNewLabeledTag(unique_id);
            start.TagGroupSetTagAsString(unique_id, value);
        }

        return start;
    }

    /**
     * Get the series definition a `TagGroup` that has the 'variable', 'start', 'step-width', 
     * 'end' and a 'on-each-point' index. The 'on-each-point' index is optional. It can contain 
     * another series with the above given indices.
     *
     * @return 
     *      The measurement series
     */
    TagGroup getSeries(object self){
        TagGroup series = NewTagGroup();
        TagGroup s = series;

        for(number i = 0; i < measurement_variables.TagGroupCountTags(); i++){
            TagGroup var = self.getSeriesSelectedMeasurementVariable(i);

            if(var.TagGroupIsValid()){
                number index;
                if(i > 0){
                    TagGroup tmp = NewTagGroup();

                    // create the 'on-each-point' index in the parent group and set the current 
                    // series to be saved to this TagGroup
                    index = s.TagGroupCreateNewLabeledTag("on-each-point");
                    s.TagGroupSetIndexedTagAsTagGroup(index, tmp);
                    s = tmp;
                }

                // save the unique_id as the variable index
                string unique_id;
                var.TagGroupGetTagAsString("unique_id", unique_id);
                index = s.TagGroupCreateNewLabeledTag("variable");
                s.TagGroupSetIndexedTagAsString(index, unique_id);

                TagGroup input;
                string value;

                // save the start
                start_inputboxes.TagGroupGetIndexedTagAsTagGroup(i, input);
                value = input.DLGGetStringValue();
                index = s.TagGroupCreateNewLabeledTag("start");
                s.TagGroupSetIndexedTagAsString(index, value);

                // save the step width
                step_inputboxes.TagGroupGetIndexedTagAsTagGroup(i, input);
                value = input.DLGGetStringValue();
                index = s.TagGroupCreateNewLabeledTag("step-width");
                s.TagGroupSetIndexedTagAsString(index, value);

                // save the end
                end_inputboxes.TagGroupGetIndexedTagAsTagGroup(i, input);
                value = input.DLGGetStringValue();
                index = s.TagGroupCreateNewLabeledTag("end");
                s.TagGroupSetIndexedTagAsString(index, value);
            }
        }

        return series;
    }

    /**
     * Add the value from the `input` to the `target` at the given `index`. The 'datatype' in the 
     * `settings` will be parsed.
     *
     * If the lenth of the `target` `TagGroup` is smaller or equal to the `index`, the value will be 
     * *inserted*, otherwise it will be *set*.
     *
     * @param input
     *      The input field as a `TagGroup`
     * @param settings
     *      The settings for the input
     * @param index
     *      The index in the `target` `TagGroup` to set the value to
     * @param target
     *      The target `TagGroup` to set the value in
     */
    void addValueFromInputToTagGroup(object self, TagGroup input, TagGroup settings, number index, TagGroup &target){
        string type;
        settings.TagGroupGetTagAsString("datatype", type);

        if(type == "int"){
            number value = input.DLGGetValue();
            if(target.TagGroupCountTags() <= index){
                target.TagGroupInsertTagAsLong(index, value);
            }
            else{
                target.TagGroupSetIndexedTagAsLong(index, value);
            }
        }
        else if(type == "float"){
            number value = input.DLGGetValue();
            if(target.TagGroupCountTags() <= index){
                target.TagGroupInsertTagAsFloat(index, value);
            }
            else{
                target.TagGroupSetIndexedTagAsFloat(index, value);
            }
        }
        else if(type == "boolean"){
            number value = input.DLGGetValue();
            if(target.TagGroupCountTags() <= index){
                target.TagGroupInsertTagAsBoolean(index, value);
            }
            else{
                target.TagGroupSetIndexedTagAsBoolean(index, value);
            }
        }
        else if(type == "options"){
            number value = input.DLGGetValue();
            TagGroup options;
            settings.TagGroupGetTagAsTagGroup("options", options);

            string str_value = "";
            if(options.TagGroupCountTags() > value){
                options.TagGroupGetIndexedTagAsString(value, str_value);
            }

            if(target.TagGroupCountTags() <= index){
                target.TagGroupInsertTagAsString(index, str_value);
            }
            else{
                target.TagGroupSetIndexedTagAsString(index, str_value);
            }
        }
        else{
            string value = input.DLGGetStringValue();
            if(target.TagGroupCountTags() <= index){
                target.TagGroupInsertTagAsString(index, value);
            }
            else{
                target.TagGroupSetIndexedTagAsString(index, value);
            }
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

        for(number j = 0; j < config_inputs.TagGroupCountTags(); j++){
            TagGroup input;
            string input_error = "";

            config_inputs.TagGroupGetIndexedTagAsTagGroup(j, input);

            string identifier;
            input.DLGGetIdentifier(identifier);
            
            string group;
            string key;
            number index;
            
            if(self.parseConfigIdentifier(identifier, group, key, index)){
                TagGroup group_tg;
                if(config_vars.TagGroupDoesTagExist(group)){
                    config_vars.TagGroupGetTagAsTagGroup(group, group_tg);
                }

                if(!group_tg.TagGroupIsValid()){
                    group_tg = NewTagGroup();
                    if(!config_vars.TagGroupDoesTagExist(group)){
                        number i = config_vars.TagGroupCreateNewLabeledTag(group);
                    }
                }

                number k = group_tg.TagGroupCreateNewLabeledTag(key);
                
                // load the settings for this value
                TagGroup group_values;
                configuration.TagGroupGetTagAsTagGroup(group, group_values);
                TagGroup value_settings;
                group_values.TagGroupGetTagAsTagGroup(key, value_settings);

                // save the value from the input with the value_settings to the key k in the group_tg
                self.addValueFromInputToTagGroup(input, value_settings, k, group_tg);

                config_vars.TagGroupSetTagAsTagGroup(group, group_tg);
            }
        }

        return config_vars;
    }

    /**
     * Get the ask for values as a `TagGroup`.
     *
     * @return
     *      The values `TagGroup`
     */
    TagGroup getAskForValues(object self){
        // TagGroup vals = NewTagGroup();
        TagGroup vals = NewTagList();

        for(number i = 0; i < ask_for_values.TagGroupCountTags(); i++){
            TagGroup input;
            ask_for_inputs.TagGroupGetIndexedTagAsTagGroup(i, input);

            TagGroup value_settings;
            ask_for_values.TagGroupGetIndexedTagAsTagGroup(i, value_settings);
            
            self.addValueFromInputToTagGroup(input, value_settings, i, vals);
        }

        return vals;
    }
}

// TagGroup m_vars = NewTagList();

// number index;
// TagGroup tg;

// // Focus Measurement variable
// tg = NewTagGroup();
// index = tg.TagGroupCreateNewLabeledTag("name");
// tg.TagGroupSetIndexedTagAsString(index, "Focus");
// index = tg.TagGroupCreateNewLabeledTag("unique_id");
// tg.TagGroupSetIndexedTagAsString(index, "focus");
// index = tg.TagGroupCreateNewLabeledTag("unit");
// tg.TagGroupSetIndexedTagAsString(index, "nm");
// index = tg.TagGroupCreateNewLabeledTag("min_value");
// tg.TagGroupSetIndexedTagAsNumber(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("max_value");
// tg.TagGroupSetIndexedTagAsNumber(index, 100);
// index = tg.TagGroupCreateNewLabeledTag("start");
// tg.TagGroupSetIndexedTagAsNumber(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("step");
// tg.TagGroupSetIndexedTagAsNumber(index, 10);
// index = tg.TagGroupCreateNewLabeledTag("end");
// tg.TagGroupSetIndexedTagAsNumber(index, 100);
// m_vars.TagGroupInsertTagAsTagGroup(infinity(), tg);

// // Tilt Measurement variable
// tg = NewTagGroup();
// index = tg.TagGroupCreateNewLabeledTag("name");
// tg.TagGroupSetIndexedTagAsString(index, "X-Tilt");
// index = tg.TagGroupCreateNewLabeledTag("unique_id");
// tg.TagGroupSetIndexedTagAsString(index, "x-tilt");
// index = tg.TagGroupCreateNewLabeledTag("unit");
// tg.TagGroupSetIndexedTagAsString(index, "deg");
// index = tg.TagGroupCreateNewLabeledTag("min_value");
// tg.TagGroupSetIndexedTagAsNumber(index, -15);
// index = tg.TagGroupCreateNewLabeledTag("max_value");
// tg.TagGroupSetIndexedTagAsNumber(index, 15);
// index = tg.TagGroupCreateNewLabeledTag("start");
// tg.TagGroupSetIndexedTagAsNumber(index, -10);
// index = tg.TagGroupCreateNewLabeledTag("step");
// tg.TagGroupSetIndexedTagAsNumber(index, 1);
// index = tg.TagGroupCreateNewLabeledTag("end");
// tg.TagGroupSetIndexedTagAsNumber(index, 10);
// m_vars.TagGroupInsertTagAsTagGroup(infinity(), tg);

// // Magnetic Field Measurement variable
// tg = NewTagGroup();
// index = tg.TagGroupCreateNewLabeledTag("name");
// tg.TagGroupSetIndexedTagAsString(index, "Magnetic Field");
// index = tg.TagGroupCreateNewLabeledTag("unique_id");
// tg.TagGroupSetIndexedTagAsString(index, "ol-current");
// index = tg.TagGroupCreateNewLabeledTag("unit");
// tg.TagGroupSetIndexedTagAsString(index, "T");
// index = tg.TagGroupCreateNewLabeledTag("min_value");
// tg.TagGroupSetIndexedTagAsNumber(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("max_value");
// tg.TagGroupSetIndexedTagAsNumber(index, 3);
// index = tg.TagGroupCreateNewLabeledTag("start");
// tg.TagGroupSetIndexedTagAsNumber(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("step");
// tg.TagGroupSetIndexedTagAsNumber(index, 0.3);
// index = tg.TagGroupCreateNewLabeledTag("end");
// tg.TagGroupSetIndexedTagAsNumber(index, 3);
// m_vars.TagGroupInsertTagAsTagGroup(infinity(), tg);

// // Condenser lense (testing only)
// tg = NewTagGroup();
// index = tg.TagGroupCreateNewLabeledTag("name");
// tg.TagGroupSetIndexedTagAsString(index, "Condenser lense");
// index = tg.TagGroupCreateNewLabeledTag("unique_id");
// tg.TagGroupSetIndexedTagAsString(index, "cl-current");
// index = tg.TagGroupCreateNewLabeledTag("unit");
// tg.TagGroupSetIndexedTagAsString(index, "hex");
// index = tg.TagGroupCreateNewLabeledTag("min_value");
// tg.TagGroupSetIndexedTagAsNumber(index, 0x0);
// index = tg.TagGroupCreateNewLabeledTag("formatted_min_value");
// tg.TagGroupSetIndexedTagAsString(index, "0x0");
// index = tg.TagGroupCreateNewLabeledTag("max_value");
// tg.TagGroupSetIndexedTagAsNumber(index, 0x8000);
// index = tg.TagGroupCreateNewLabeledTag("formatted_max_value");
// tg.TagGroupSetIndexedTagAsString(index, "0x8000");
// index = tg.TagGroupCreateNewLabeledTag("start");
// tg.TagGroupSetIndexedTagAsNumber(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("formatted_start");
// tg.TagGroupSetIndexedTagAsString(index, "0x0");
// index = tg.TagGroupCreateNewLabeledTag("step");
// tg.TagGroupSetIndexedTagAsNumber(index, 0x100);
// index = tg.TagGroupCreateNewLabeledTag("formatted_step");
// tg.TagGroupSetIndexedTagAsString(index, "0x100");
// index = tg.TagGroupCreateNewLabeledTag("end");
// tg.TagGroupSetIndexedTagAsNumber(index, 0x8000);
// index = tg.TagGroupCreateNewLabeledTag("formatted_end");
// tg.TagGroupSetIndexedTagAsString(index, "0x8000");
// index = tg.TagGroupCreateNewLabeledTag("format");
// tg.TagGroupSetIndexedTagAsString(index, "hex");
// m_vars.TagGroupInsertTagAsTagGroup(infinity(), tg);
// TagGroup config_vars = NewTagGroup();

// // number index;
// // TagGroup tg, tg2;
// TagGroup tg2;

// tg = NewTagGroup();

// tg2 = NewTagGroup();
// index = tg2.TagGroupCreateNewLabeledTag("value");
// tg2.TagGroupSetIndexedTagAsString(index, "camera");
// index = tg2.TagGroupCreateNewLabeledTag("default_value");
// tg2.TagGroupSetIndexedTagAsString(index, "");
// index = tg2.TagGroupCreateNewLabeledTag("datatype");
// tg2.TagGroupSetIndexedTagAsString(index, "string");
// index = tg2.TagGroupCreateNewLabeledTag("description");
// tg2.TagGroupSetIndexedTagAsString(index, "the detector to use to acquire the image");
// index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg2.TagGroupCreateNewLabeledTag("restart_required");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("detector-name");
// tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

// tg2 = NewTagGroup();
// index = tg2.TagGroupCreateNewLabeledTag("value");
// tg2.TagGroupSetIndexedTagAsNumber(index, 1024);
// index = tg2.TagGroupCreateNewLabeledTag("default_value");
// tg2.TagGroupSetIndexedTagAsString(index, "");
// index = tg2.TagGroupCreateNewLabeledTag("datatype");
// tg2.TagGroupSetIndexedTagAsString(index, "int");
// index = tg2.TagGroupCreateNewLabeledTag("description");
// tg2.TagGroupSetIndexedTagAsString(index, "the size (width has to be equal to height) of the image the detector makes in px");
// index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg2.TagGroupCreateNewLabeledTag("restart_required");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("image-size");
// tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

// index = config_vars.TagGroupCreateNewLabeledTag("pyjem-camera");
// config_vars.TagGroupSetIndexedTagAsTagGroup(index, tg);

// tg = NewTagGroup();

// tg2 = NewTagGroup();
// index = tg2.TagGroupCreateNewLabeledTag("value");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 1);
// index = tg2.TagGroupCreateNewLabeledTag("default_value");
// tg2.TagGroupSetIndexedTagAsString(index, "");
// index = tg2.TagGroupCreateNewLabeledTag("datatype");
// tg2.TagGroupSetIndexedTagAsString(index, "boolean");
// index = tg2.TagGroupCreateNewLabeledTag("description");
// tg2.TagGroupSetIndexedTagAsString(index, "Whether to set the microscope in the safe sate after the measurement is finished");
// index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg2.TagGroupCreateNewLabeledTag("restart_required");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("microscope-to-safe-state-after-measurement");
// tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

// tg2 = NewTagGroup();
// index = tg2.TagGroupCreateNewLabeledTag("value");
// tg2.TagGroupSetIndexedTagAsFloat(index, 3.5);
// index = tg2.TagGroupCreateNewLabeledTag("default_value");
// tg2.TagGroupSetIndexedTagAsString(index, "");
// index = tg2.TagGroupCreateNewLabeledTag("datatype");
// tg2.TagGroupSetIndexedTagAsString(index, "float");
// index = tg2.TagGroupCreateNewLabeledTag("description");
// tg2.TagGroupSetIndexedTagAsString(index, "The relaxation time in seconds to wait after the microscope is switched to lorentz mode. Use 0 or negative values to ignore");
// index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg2.TagGroupCreateNewLabeledTag("restart_required");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("relaxation-time-lorentz-mode");
// tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

// string path = GetApplicationDirectory("auto_save", 1)
// tg2 = NewTagGroup();
// index = tg2.TagGroupCreateNewLabeledTag("value");
// tg2.TagGroupSetIndexedTagAsString(index, path + "\\1990-01-01\\");
// index = tg2.TagGroupCreateNewLabeledTag("default_value");
// tg2.TagGroupSetIndexedTagAsString(index, "");
// index = tg2.TagGroupCreateNewLabeledTag("datatype");
// tg2.TagGroupSetIndexedTagAsString(index, "string");
// index = tg2.TagGroupCreateNewLabeledTag("description");
// tg2.TagGroupSetIndexedTagAsString(index, "The directory where to save the camera images to that are recorded while measuring");
// index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg2.TagGroupCreateNewLabeledTag("restart_required");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("save-directory");
// tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

// tg2 = NewTagGroup();
// index = tg2.TagGroupCreateNewLabeledTag("value");
// tg2.TagGroupSetIndexedTagAsString(index, "{counter}_{time:%Y-%m-%d_%H-%M-%S}_lorentz-measurement.dm4");
// index = tg2.TagGroupCreateNewLabeledTag("default_value");
// tg2.TagGroupSetIndexedTagAsString(index, "");
// index = tg2.TagGroupCreateNewLabeledTag("datatype");
// tg2.TagGroupSetIndexedTagAsString(index, "string");
// index = tg2.TagGroupCreateNewLabeledTag("description");
// tg2.TagGroupSetIndexedTagAsString(index, "The name format to use to save the recorded images. Some placeholders can be used. Use {counter} to get the current measurement number, use {tags[your_value]} to get use the `your_value` of the measurement tags. Use {variables[your_variable]} to get the value of the measurement variable `your_variable`. To use the `your_img_value` of the image tags, use {imgtags[your_value]}. For times set the format according to the python `strftime()` format, started with a colon (:), like {time:%Y-%m-%d_%H-%M-%S} for year, month, day and hour minute and second. Make sure to inculde the file extension but use supported extensions only.");
// index = tg2.TagGroupCreateNewLabeledTag("ask_if_not_present");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg2.TagGroupCreateNewLabeledTag("restart_required");
// tg2.TagGroupSetIndexedTagAsBoolean(index, 0);
// index = tg.TagGroupCreateNewLabeledTag("save-file-format");
// tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);

// index = config_vars.TagGroupCreateNewLabeledTag("measurement");
// config_vars.TagGroupSetIndexedTagAsTagGroup(index, tg);

// dialog_startup, m_vars and config_vars are defined in the python file executing this file
// TagGroup m_vars = NewTagList();
// TagGroup config_vars = NewTagList();
// string dialog_startup = "series"; 
// string __file__ = getApplicationDirectory(0, 1);
string title = "PyLo";

object dialog = alloc(DMViewDialog).init(dialog_startup, title, m_vars, config_vars, ask_vals, message);

TagGroup start;
TagGroup series;
TagGroup configuration;
TagGroup ask_for;
number success;

if(dialog_startup == "series"){
    success = dialog.poseSeries();
}
else if(dialog_startup == "configuration"){
    success = dialog.poseConfiguration();
}
else{
    success = dialog.pose();
}

if(success){
    start = dialog.getStart();
    series = dialog.getSeries();
    configuration = dialog.getConfiguration();
    ask_for = dialog.getAskForValues();
}