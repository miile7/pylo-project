/**
 * Returns whether the `text` contains numbers and optional one dot and optional one minus at the 
 * start only. Note that any added whitespace will return false already.
 *
 * @param text
 *      The text to check
 *
 * @return
 *      Whether the `text` is a valid number expression or not
 */
number is_numeric(string text){
    if(text == ""){
        return 0;
    }

    number minus_found = 0;
    number dot_found = 0;

    for(number i = 0; i < text.len(); i++){
        string c = text.mid(i, 1);
        number a = asc(c);

        if((a < 48 || a > 57) && (i != 0 || c != "-") && (dot_found || c != ".")){
            return 0;
        }
    }

    return 1;
}

/**
 * Removes the entry with the given `index` from the choice `container`.
 *
 * @param container
 *      The dialog choice
 * @param index
 *      The index
 *
 * @return 
 *      The choice container
 */
TagGroup DLGRemoveChoiceItemEntry(TagGroup container, number index){
    TagGroup items;
    container.TagGroupGetTagAsTagGroup("Items", items);
    items.TagGroupDeleteTagWithIndex(index);
    container.TagGroupSetTagAsTagGroup("Items", items);

    return container;
}

/**
 * Removes the entry with the given `label` from the choice `container`.
 *
 * @param container
 *      The dialog choice
 * @param label
 *      The label of the choice item
 *
 * @return 
 *      The choice container
 */
TagGroup DLGRemoveChoiceItemEntry(TagGroup container, string label){
    TagGroup items;
    container.TagGroupGetTagAsTagGroup("Items", items);

    for(number i = 0; i < items.TagGroupCountTags(); i++){
        TagGroup item;
        items.TagGroupGetIndexedTagAsTagGroup(i, item);

        string l;
        item.TagGroupGetTagAsString("Label", l);

        if(l == label){
            items.TagGroupDeleteTagWithIndex(i);
            break;
        }
    }

    container.TagGroupSetTagAsTagGroup("Items", items);

    return container;
    
}

/**
 * The dialog to show for the settings and the series select.
 */
class DMViewDialog : UIFrame{
    /**
     * The `MeasurementVariable`s as a TagList. Each entry contains a TagGroup which represents the 
     * python `MeasurementVariable` object. Each attribute of the object can be received with the
     * same name in the TagGroup exteded with the `start`, `step_width` and `end` keys that contain
     * the corresponding (formatted) values. The `datatype` is either 'string', 'int' or 'float' as 
     * a string.
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
        parsable = is_numeric(value);
        return value.val();
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
        
        if(is_numeric(identifier)){
            // convert to a number
            number index = identifier.val();
            return index;
        }

        return -1;
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
        string min_value;
        string max_value;
        
        measurement_variable.TagGroupGetTagAsString("min_value", min_value);
        measurement_variable.TagGroupGetTagAsString("max_value", max_value);

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
            string start;
            var.TagGroupGetTagAsString("start", start);
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
            string step;
            var.TagGroupGetTagAsString("step", step);
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
            string end;
            var.TagGroupGetTagAsString("end", end);
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

        // TagGroup error_headline = DLGCreateLabel("Errors:");
        // wrapper.DLGAddElement(error_headline);
        TagGroup error_box = DLGCreateBox("Errors");

        error_display = DLGCreateLabel("Currently no errors", 100);
        error_display.DLGHeight(2);
        error_display.DLGExpand("X");
        error_display.DLGFill("X");
        // wrapper.DLGAddElement(error_display);
        error_box.DLGAddElement(error_display);
        wrapper.DLGAddElement(error_box);

        // save all start value input boxes in a group
        start_value_inputboxes = NewTagGroup();

        // the number of variables to show in one row
        number max_rows = 1;

        TagGroup upper_wrapper = DLGCreateBox("Start parameters");
        upper_wrapper.DLGTableLayout(max_rows * 3, ceil(measurement_variables.TagGroupCountTags() / max_rows), 0);
        upper_wrapper.DLGExpand("X");
        upper_wrapper.DLGFill("X");

        // go through the measurement variables and add all the start input boxes
        for(number j = 0; j < measurement_variables.TagGroupCountTags(); j++){
            TagGroup var = self._getMeasurementVariableByIndex(j);

            string unique_id;
            var.TagGroupGetTagAsString("unique_id", unique_id);

            string label = self._getMeasurementVariableLabel(var);
            string limits = self._getMeasurementVariableLimits(var);

            TagGroup label_element = DLGCreateLabel(label, 20);
            label_element.DLGAnchor("East");
            upper_wrapper.DLGAddElement(label_element);
            
            string start;
            var.TagGroupGetTagAsString("start", start);

            TagGroup start_input = DLGCreateStringField(start, 8, "startChangedCallback");
            start_input.DLGAnchor("West");
            start_input.DLGIdentifier("start_value-" + unique_id);

            // add the input box to the internal list to access them later on
            number index = start_value_inputboxes.TagGroupCreateNewLabeledTag(unique_id);
            start_value_inputboxes.TagGroupSetIndexedTagAsTagGroup(index, start_input);
            
            // add the start
            upper_wrapper.DLGAddElement(start_input);
            // add the limits
            upper_wrapper.DLGAddElement(DLGCreateLabel(limits, 15));
        }

        wrapper.DLGAddElement(upper_wrapper);

        // prepare the series paramter inputs
        TagGroup lower_wrapper = DLGCreateBox("Series parameters");

        // number of input rows
        number c = measurement_variables.TagGroupCountTags();

        // column widths
        number cw2 = 10;
        number cw3 = 10;
        number cw4 = 10;
        number cw5 = 10;
        
        // header
        TagGroup input_line = self._createInputLine(4);
        input_line.DLGAddElement(DLGCreateLabel("Series over...", 34));
        input_line.DLGAddElement(DLGCreateLabel("Start", cw3));
        input_line.DLGAddElement(DLGCreateLabel("Step width", cw4));
        input_line.DLGAddElement(DLGCreateLabel("End", cw5));

        lower_wrapper.DLGAddElement(input_line);
        lower_wrapper.DLGExpand("X");
        lower_wrapper.DLGFill("X");

        // item lists
        series_selectboxes = NewTagList();
        limit_displays = NewTagList();
        start_inputboxes = NewTagList();
        step_inputboxes = NewTagList();
        end_inputboxes = NewTagList();
        on_each_labels = NewTagList();

        // add measurement variable rows
        for(number i = 0; i < c ; i++){
            TagGroup input_line = self._createInputLine(5);
            TagGroup series_select = DLGCreateChoice(0, "seriesSelectChanged");
            // padding has to be negative, don't know why, otherwise it is in the wrong direction,
            // also setting padding for right value does the wrong outcome
            series_select.DLGExternalPadding(0, i * -50, 0, 0);
            series_select.DLGWidth(100);
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
                TagGroup on_each_label = DLGCreateLabel("", 60);
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
            TagGroup label = DLGCreateLabel(message, 100);
            label.DLGHeight(3);
            dialog_items.DLGAddElement(label);
        }
        
        dialog_items.DLGAddElement(self._createSeriesSetupContent());

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
	object init(object self, string title, TagGroup measurement_vars, string message){
        measurement_variables = measurement_vars;
		self.super.init(self._createContent(title, message));
        
		return self;
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
}

TagGroup m_vars = NewTagList();

number index;
TagGroup tg;

// Focus Measurement variable
tg = NewTagGroup();
index = tg.TagGroupCreateNewLabeledTag("name");
tg.TagGroupSetIndexedTagAsString(index, "Focus");
index = tg.TagGroupCreateNewLabeledTag("unique_id");
tg.TagGroupSetIndexedTagAsString(index, "focus");
index = tg.TagGroupCreateNewLabeledTag("unit");
tg.TagGroupSetIndexedTagAsString(index, "nm");
index = tg.TagGroupCreateNewLabeledTag("min_value");
tg.TagGroupSetIndexedTagAsNumber(index, 0);
index = tg.TagGroupCreateNewLabeledTag("max_value");
tg.TagGroupSetIndexedTagAsNumber(index, 100);
index = tg.TagGroupCreateNewLabeledTag("start");
tg.TagGroupSetIndexedTagAsNumber(index, 0);
index = tg.TagGroupCreateNewLabeledTag("step");
tg.TagGroupSetIndexedTagAsNumber(index, 10);
index = tg.TagGroupCreateNewLabeledTag("end");
tg.TagGroupSetIndexedTagAsNumber(index, 100);
m_vars.TagGroupInsertTagAsTagGroup(infinity(), tg);

// Tilt Measurement variable
tg = NewTagGroup();
index = tg.TagGroupCreateNewLabeledTag("name");
tg.TagGroupSetIndexedTagAsString(index, "X-Tilt");
index = tg.TagGroupCreateNewLabeledTag("unique_id");
tg.TagGroupSetIndexedTagAsString(index, "x-tilt");
index = tg.TagGroupCreateNewLabeledTag("unit");
tg.TagGroupSetIndexedTagAsString(index, "deg");
index = tg.TagGroupCreateNewLabeledTag("min_value");
tg.TagGroupSetIndexedTagAsNumber(index, -15);
index = tg.TagGroupCreateNewLabeledTag("max_value");
tg.TagGroupSetIndexedTagAsNumber(index, 15);
index = tg.TagGroupCreateNewLabeledTag("start");
tg.TagGroupSetIndexedTagAsNumber(index, -10);
index = tg.TagGroupCreateNewLabeledTag("step");
tg.TagGroupSetIndexedTagAsNumber(index, 1);
index = tg.TagGroupCreateNewLabeledTag("end");
tg.TagGroupSetIndexedTagAsNumber(index, 10);
m_vars.TagGroupInsertTagAsTagGroup(infinity(), tg);

// Magnetic Field Measurement variable
tg = NewTagGroup();
index = tg.TagGroupCreateNewLabeledTag("name");
tg.TagGroupSetIndexedTagAsString(index, "Magnetic Field");
index = tg.TagGroupCreateNewLabeledTag("unique_id");
tg.TagGroupSetIndexedTagAsString(index, "ol-current");
index = tg.TagGroupCreateNewLabeledTag("unit");
tg.TagGroupSetIndexedTagAsString(index, "T");
index = tg.TagGroupCreateNewLabeledTag("min_value");
tg.TagGroupSetIndexedTagAsNumber(index, 0);
index = tg.TagGroupCreateNewLabeledTag("max_value");
tg.TagGroupSetIndexedTagAsNumber(index, 3);
index = tg.TagGroupCreateNewLabeledTag("start");
tg.TagGroupSetIndexedTagAsNumber(index, 0);
index = tg.TagGroupCreateNewLabeledTag("step");
tg.TagGroupSetIndexedTagAsNumber(index, 0.3);
index = tg.TagGroupCreateNewLabeledTag("end");
tg.TagGroupSetIndexedTagAsNumber(index, 3);
m_vars.TagGroupInsertTagAsTagGroup(infinity(), tg);

// Condenser lense (testing only)
tg = NewTagGroup();
index = tg.TagGroupCreateNewLabeledTag("name");
tg.TagGroupSetIndexedTagAsString(index, "Condenser lense");
index = tg.TagGroupCreateNewLabeledTag("unique_id");
tg.TagGroupSetIndexedTagAsString(index, "cl-current");
index = tg.TagGroupCreateNewLabeledTag("unit");
tg.TagGroupSetIndexedTagAsString(index, "hex");
index = tg.TagGroupCreateNewLabeledTag("min_value");
tg.TagGroupSetIndexedTagAsNumber(index, 0x0);
index = tg.TagGroupCreateNewLabeledTag("formatted_min_value");
tg.TagGroupSetIndexedTagAsString(index, "0x0");
index = tg.TagGroupCreateNewLabeledTag("max_value");
tg.TagGroupSetIndexedTagAsNumber(index, 0x8000);
index = tg.TagGroupCreateNewLabeledTag("formatted_max_value");
tg.TagGroupSetIndexedTagAsString(index, "0x8000");
index = tg.TagGroupCreateNewLabeledTag("start");
tg.TagGroupSetIndexedTagAsNumber(index, 0);
index = tg.TagGroupCreateNewLabeledTag("formatted_start");
tg.TagGroupSetIndexedTagAsString(index, "0x0");
index = tg.TagGroupCreateNewLabeledTag("step");
tg.TagGroupSetIndexedTagAsNumber(index, 0x100);
index = tg.TagGroupCreateNewLabeledTag("formatted_step");
tg.TagGroupSetIndexedTagAsString(index, "0x100");
index = tg.TagGroupCreateNewLabeledTag("end");
tg.TagGroupSetIndexedTagAsNumber(index, 0x8000);
index = tg.TagGroupCreateNewLabeledTag("formatted_end");
tg.TagGroupSetIndexedTagAsString(index, "0x8000");
index = tg.TagGroupCreateNewLabeledTag("format");
tg.TagGroupSetIndexedTagAsString(index, "hex");
m_vars.TagGroupInsertTagAsTagGroup(infinity(), tg);

object dialog = alloc(DMViewDialog).init("Create lorenz mode measurement -- PyLo", m_vars, "Create a new measurememt series to measure probes in the lorenz mode (low mag mode). Select the start properties. The series defines over which variables the series will be done. On each series point there can be another series.");

if(dialog.pose()){
    // TagGroup start = dialog.getStart();
    // TagGroup series = dialog.getSeries();

    // start.TagGroupOpenBrowserWindow(0);
    // series.TagGroupOpenBrowserWindow(0);
}