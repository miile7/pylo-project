/**
 * Returns how many times the `value` occurres in the TagList `tg`.
 *
 * @param tg
 *      The TagList
 * @param value
 *      The value to compare
 *
 * @return
 *      The number of times the `value` is in the TagList
 */
number count_occurances(TagGroup tg, string value){
    number count = 0;

    for(number i = 0; i < tg.TagGroupCountTags(); i++){
        String v;
        tg.TagGroupGetIndexedTagAsString(i, v);

        if(v == value){
            count++;
        }
    }

    return count;
}

/**
 * Show the given `TagList`s contents (if they are strings) in the results output.
 */
void show_tag_list(TagGroup tl){
    result("TagList[\n")
    for(number i = 0; i < tl.TagGroupCountTags(); i++){
        string val;
        tl.TagGroupGetIndexedTagAsString(i, val);
        result("  " + i + ": '" + val + "'\n");
    }
    result("]\n");
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
     * A TagList that contains a TagGroup on each index. Each TagGroup has an 'index' and a 'id' key.
     * The 'index' holds the row index in the dialog, the 'id' holds the unique Measurement Variable
     * id this row contains.
     */
    TagGroup index_variable_map;

    /**
     * A TagList that contains all the labels in each row telling which measurement variable is
     * modified.
     */
    TagGroup row_labels;

    /**
     * A TagList that contains all the selectboxes for selecting the type (series or fixed value).
     */
    TagGroup type_selectboxes;

    /**
     * A TagList that contains all the input boxes for the start values.
     */
    TagGroup start_inputboxes;

    /**
     * A TagList that contains all the input boxes for the step width values.
     */
    TagGroup step_inputboxes;

    /**
     * A TagList that contains all the input boxes for the end values.
     */
    TagGroup end_inputboxes;

    /**
     * The buttons for swapping upwards
     */
    TagGroup swap_upwards_buttons;

    /**
     * The buttons for swapping downwards
     */
    TagGroup swap_downwards_buttons;

    /**
     * A TagList that contains all the value limits.
     */
    TagGroup value_limits;

    /**
     * Return an image of an arrow pointing upwards
     *
     * @return
     *      The arrow image
     */
    RGBImage _drawUpArrow(object self){
        number imgw = 16;
        number imgh = 16;

        rgbimage aline := RGBImage("arrow-line", 4, imgw, imgh);
        rgbimage ahead := RGBImage("arrow-head", 4, imgw, imgh);
        rgbimage img := RGBImage("arrow", 4, imgw, imgh);

        // width of the arrow line (twice as wide for even images)
        number w = 2;
        // padding bottom and top of the arrow line
        number p = 2
        // width of the arrow head
        number hw = imgw / 4;
        // height of the arrow head
        number hh = imgh / 4;

        // draw the line
        aline = abs(icol + 0.5 - iwidth / 2) < w && irow > p + hh && irow < iheight - p ? 255 : 0;
        // draw the triangle
        ahead = abs(hh / hw * (icol + 0.5  - iwidth/2)) < irow && irow <= hh + p ? 255 : 0;

        // combine both images
        img = (aline + ahead);
        
        return img;
    }

    /** 
     * Return an image of an arrow pointing downwards
     *
     * @return
     *      The arrow image
     */
    RGBImage _drawDownArrow(object self){
        RGBImage up_arrow = self._drawUpArrow();
        number width;
        number height;
        up_arrow.getsize(width, height);

		RGBImage down_arrow = RGBImage("arrow", 4, width, height);
        down_arrow = up_arrow[icol, iheight - irow];
        return down_arrow;
    }

    /**
     * Show the measurement variables and the row-variable map in the results output.
     */
    void _debugMeasurementVariables(object self){
        result("measurement_variables = [");
        for(number i = 0; i < measurement_variables.TagGroupCountTags(); i++){
            TagGroup tg;
            measurement_variables.TagGroupGetIndexedTagAsTagGroup(i, tg);

            String id;
            tg.TagGroupGetTagAsString("unique_id", id);
            result(i + "=" + id);

            if(i + 1 < measurement_variables.TagGroupCountTags()){
                result(", ");
            }
        }
        result("]\n");

        result("index_variable_map = [");
        for(number i = 0; i < index_variable_map.TagGroupCountTags(); i++){
            string id;
            index_variable_map.TagGroupGetIndexedTagAsString(i, id);
            result(i + "=>" + id);

            if(i + 1 < index_variable_map.TagGroupCountTags()){
                result(", ");
            }
        }
        result("]\n");
    }

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
     * Get the row index for the given measurement variable `unique_id`.
     *
     * @see DMViewDialog::getMeasurementVariableIdForRowIndex()
     *
     * @param unique_id
     *      The id of the measurement variable to get
     * 
     * @return
     *      The index or -1 if the `unique_id` does not exist
     */
    number getRowIndexForMeasurementVariableId(object self, string unique_id){
        for(number i = 0; i < index_variable_map.TagGroupCountTags(); i++){
            string id;
            index_variable_map.TagGroupGetIndexedTagAsString(i, id);
            
            if(id == unique_id){
                return i;
            }
        }

        return -1;
    }

    /**
     * Get the measurement variable `unique_id` for the given row `index`.
     *
     * @see DMViewDialog::getRowIndexForMeasurementVariableId()
     *
     * @param index
     *      The row index, zero-based
     * 
     * @return
     *      The unique id of the measurement variable or an empty string if the index does not exist
     */
    string getMeasurementVariableIdForRowIndex(object self, number index){
        string unique_id = "";
        if(0 <= index && index < index_variable_map.TagGroupCountTags()){
            index_variable_map.TagGroupGetIndexedTagAsString(index, unique_id);
        }

        return unique_id;
    }

    /**
     * Set the row with the given `index` to display the given `measurement_variable`.
     *
     * A `measurement_variable` is a `TagGroup` with the following indices:
     * - "name", string: The name/label to show
     * - "unit", string: The unit, to not show a unit use "" (empty string)
     * - "series-type", number, optional: Either 0 for using the value as fixed or 1 to use it as a 
     *   series, if not given the current value will be kept
     * - "start", string: The start value to display in the "unit" units
     * - "step", string: The step width value to display in the "unit" units
     * - "end", string: The end value to display in the "unit" units
     * - "min_value", string: The minimum value, to not show a minimum value use "" (empty string)
     * - "max_value", string: The maximum value, to not show a maximum value use "" (empty string)
     *
     * The `measurement_variable` will be saved for the `index` in the 
     * `DMViewDialog::index_variable_map`.
     *
     * @param measurement_variable
     *      The measurement variable `TagGroup` to set, this is not validated
     * @param index
     *      The row index
     */
    void setMeasurementVariableToRow(object self, TagGroup measurement_variable, number index){
        // the label, includes the unit
        TagGroup row_label;
        string name;
        string unit;
        measurement_variable.TagGroupGetTagAsString("name", name);
        measurement_variable.TagGroupGetTagAsString("unit", unit);
        row_labels.TagGroupGetIndexedTagAsTagGroup(index, row_label);
        if(unit != ""){
            name += " [" + unit + "]";
        }
        row_label.DLGTitle(name);

        // choice, if exists
        TagGroup type_select;
        type_selectboxes.TagGroupGetIndexedTagAsTagGroup(index, type_select);
        if(measurement_variable.TagGroupDoesTagExist("series-type")){
            number selected_index;
            measurement_variable.TagGroupGetTagAsShort("series-type", selected_index);
            type_select.DLGValue(selected_index);
        }
        else{
            number i = measurement_variable.TagGroupCreateNewLabeledTag("series-type");
            measurement_variable.TagGroupSetIndexedTagAsShort(i, type_select.DLGGetValue());
        }

        // the start value
        TagGroup start_input;
        string start_value;
        measurement_variable.TagGroupGetTagAsString("start", start_value);
        start_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, start_input);
        start_input.DLGValue(start_value);

        // the step width value
        TagGroup step_input;
        string step_value;
        measurement_variable.TagGroupGetTagAsString("step", step_value);
        step_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, step_input);
        step_input.DLGValue(step_value);

        // the end value
        TagGroup end_input;
        string end_value;
        measurement_variable.TagGroupGetTagAsString("end", end_value);
        end_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, end_input);
        end_input.DLGValue(end_value);

        // boundaries
        TagGroup limits_input;
        string min_value = "";
        string max_value = "";
        measurement_variable.TagGroupGetTagAsString("min_value", min_value);
        measurement_variable.TagGroupGetTagAsString("max_value", max_value);
        value_limits.TagGroupGetIndexedTagAsTagGroup(index, limits_input);
        string limits = "";
        if(min_value != "" && max_value != ""){
            limits += min_value + ".." + max_value;
        }
        else if(min_value != ""){
            limits += ">= " + min_value;
            // limits += "≥ " + min_value;
        }
        else if(max_value != ""){
            limits += "<= " + max_value;
            // limits += "≤ " + max_value;
        }

        if(limits != ""){
            limits = "[" + limits + "]";
        }
        limits_input.DLGTitle(limits);

        for(number i = index_variable_map.TagGroupCountTags(); i <= index; i++){
            // cannot access indices directly, add dummies if the map does not contain enough 
            // elements
            index_variable_map.TagGroupInsertTagAsString(i, "");
        }

        string unique_id;
        measurement_variable.TagGroupGetTagAsString("unique_id", unique_id);
        index_variable_map.TagGroupSetIndexedTagAsString(index, unique_id);
    }

    /**
     * Saves all measurement variable inputs to the internal `DMViewDialog::measurement_variables`.
     */
    void saveMeasurementVariableInputs(object self){
        for(number i = 0; i < measurement_variables.TagGroupCountTags(); i++){
            TagGroup measurement_variable = self._getMeasurementVariableByIndex(i);
            string unique_id;
            measurement_variable.TagGroupGetTagAsString("unique_id", unique_id);

            number index = self.getRowIndexForMeasurementVariableId(unique_id);

            // series type select
            TagGroup type_select;
            type_selectboxes.TagGroupGetIndexedTagAsTagGroup(index, type_select);
            if(!measurement_variable.TagGroupDoesTagExist("series-type")){
                number j = measurement_variable.TagGroupCreateNewLabeledTag("series-type");
                measurement_variable.TagGroupSetIndexedTagAsShort(j, type_select.DLGGetValue());
            }
            else{
                measurement_variable.TagGroupSetTagAsShort("series-type", type_select.DLGGetValue());
            }

            // start
            TagGroup start_input;
            start_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, start_input);
            measurement_variable.TagGroupSetTagAsString("start", start_input.DLGGetStringValue());

            // step width
            TagGroup step_input;
            step_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, step_input);
            measurement_variable.TagGroupSetTagAsString("step", step_input.DLGGetStringValue());

            // end
            TagGroup end_input;
            end_inputboxes.TagGroupGetIndexedTagAsTagGroup(index, end_input);
            measurement_variable.TagGroupSetTagAsString("end", end_input.DLGGetStringValue());

            // save the values
            measurement_variables.TagGroupSetIndexedTagAsTagGroup(i, measurement_variable);
        }
    }

    /**
     * Swap the `row_index1`-th row with the `row_index2`-th row and the `row_index2`-th row with 
     * the `row_index1`-th row. If one of the row indices is invalid or if the indices are the same, 
     * 0 is returned and no rows will be swapped.
     *
     * Note that this saves all measurement variables inputs.
     *
     * @param row_index1
     *      The index of one row
     * @param row_index2
     *      The index of the other row
     *
     * @return
     *      1 if the rows were swapped successfully, 0 if not
     */
    number swapRows(object self, number row_index1, number row_index2){
        self._debugMeasurementVariables();
        self.saveMeasurementVariableInputs();
        number c = measurement_variables.TagGroupCountTags();

        if(row_index1 != row_index2 && 0 <= row_index1 && row_index1 < c && 0 <= row_index2 && row_index2 < c){
            string var_id1 = self.getMeasurementVariableIdForRowIndex(row_index1);
            string var_id2 = self.getMeasurementVariableIdForRowIndex(row_index2);
            TagGroup var1 = self._getMeasurementVariableById(var_id1);
            TagGroup var2 = self._getMeasurementVariableById(var_id2);

            self.setMeasurementVariableToRow(var1, row_index2);
            self.setMeasurementVariableToRow(var2, row_index1);

            self._debugMeasurementVariables();
            return 1;
        }
        return 0;
    }

    /**
     * Swap the `index`-th row with the row one above. If there is no row above, nothing will happen 
     * and 0 will be returned, 1 otherwise.
     *
     * @param index
     *      The index of the row to move one row upwards
     *
     * @return
     *      1 if the rows were swapped successfully, 0 if not
     */
    number swapWithUpper(object self, number index){
        return self.swapRows(index, index - 1);
    }

    /**
     * Swap the `index`-th row with the row one below. If there is no row below, nothing will happen 
     * and 0 will be returned, 1 otherwise.
     *
     * @param index
     *      The index of the row to move one row downwards
     *
     * @return
     *      1 if the rows were swapped successfully, 0 if not
     */
    number swapWithLower(object self, number index){
        return self.swapRows(index, index + 1);
    }

    /**
     * The callback for the swap upwards button.
     */
    void swapUpwardsCallback(object self){
        for(number i = 0; i < swap_upwards_buttons.TagGroupCountTags(); i++){
            TagGroup button;
            swap_upwards_buttons.TagGroupGetIndexedTagAsTagGroup(i, button);

            if(button.DLGGetValue() == 1){
                // this button is pressed
                self.swapWithUpper(i);
                button.DLGBevelButtonOn(0);
                break;
            }
        }
    }

    /**
     * The callback for the swap upwards button.
     */
    void swapDownwardsCallback(object self){
        for(number i = 0; i < swap_downwards_buttons.TagGroupCountTags(); i++){
            TagGroup button;
            swap_downwards_buttons.TagGroupGetIndexedTagAsTagGroup(i, button);

            if(button.DLGGetValue() == 1){
                // this button is pressed
                self.swapWithLower(i);
                button.DLGBevelButtonOn(0);
                break;
            }
        }
    }

    /**
     * Create the series start, step or end input
     *
     * @param type
     *      The type, use 'start', 'step' or 'end'
     * @param index
     *      The row index
     *
     * @return
     *      The input
     */
    TagGroup _createSeriesInput(object self, string type, number index){
        TagGroup input = DLGCreateStringField("", 6);
        input.DLGIdentifier("series_input_" + type + "_" + index);
        return input;
    }

    /**
     * Add one row for setting the measurement variables for the series to the `wrapper`.
     *
     * @param index
     *      The row index
     * @param wrapper
     *      The wrapper
     *
     * @return
     *      The wrapper with the added row
     */
    TagGroup _addSeriesRow(object self, number index, TagGroup wrapper){
        // set the label
        TagGroup row_label = DLGCreateLabel("Label " + index);
        row_label.DLGIdentifier("rowlabel" + index);
        row_labels.TagGroupInsertTagAsTagGroup(infinity(), row_label);
        wrapper.DLGAddElement(row_label);

        // the variable select
        TagGroup type_select = DLGCreateChoice(1);
        type_select.DLGAddChoiceItemEntry("Series");
        type_select.DLGAddChoiceItemEntry("Fixed Value");
        type_select.DLGIdentifier("type_select-" + index);
        type_selectboxes.TagGroupInsertTagAsTagGroup(infinity(), type_select);
        wrapper.DLGAddElement(type_select);

        // the start
        TagGroup start_input = self._createSeriesInput("start", index);
        start_inputboxes.TagGroupInsertTagAsTagGroup(infinity(), start_input);
        wrapper.DLGAddElement(start_input);

        // the step width
        TagGroup step_input = self._createSeriesInput("step", index);
        step_inputboxes.TagGroupInsertTagAsTagGroup(infinity(), step_input);
        wrapper.DLGAddElement(step_input);

        // the end width
        TagGroup end_input = self._createSeriesInput("end", index);
        end_inputboxes.TagGroupInsertTagAsTagGroup(infinity(), end_input);
        wrapper.DLGAddElement(end_input);

        // limits
        TagGroup value_limit = DLGCreateLabel("[..]");
        value_limit.DLGIdentifier("value_limit-" + index);
        value_limits.TagGroupInsertTagAsTagGroup(infinity(), value_limit);
        wrapper.DLGAddElement(value_limit);

        // order buttons
        rgbimage up_img = self._drawUpArrow();
        // TagGroup up_button = DLGCreateBevelButton(up_img, up_img, "swapUpwardsCallback");
        // up_button.DLGIdentifier("up_button-" + index);
        TagGroup up_button = DLGCreateDualStateBevelButton("up_button-" + index, up_img, up_img, "swapUpwardsCallback");
        if(index == 0){
            up_button.DLGEnabled(0);
        }
        swap_upwards_buttons.TagGroupInsertTagAsTagGroup(infinity(), up_button);
        wrapper.DLGAddElement(up_button);

        rgbimage down_img = self._drawDownArrow();
        // TagGroup down_button = DLGCreateBevelButton(down_img, down_img, "swapDownwardsCallback");
        // down_button.DLGIdentifier("down_button-" + index);
        TagGroup down_button = DLGCreateDualStateBevelButton("down_button-" + index, down_img, down_img, "swapDownwardsCallback");
        if(index + 1 == measurement_variables.TagGroupCountTags()){
            down_button.DLGEnabled(0);
        }
        swap_downwards_buttons.TagGroupInsertTagAsTagGroup(infinity(), down_button);
        wrapper.DLGAddElement(down_button);

        return wrapper;
    }

    TagGroup _createSeriesPanelContent(object self){
        TagGroup wrapper = DLGCreateGroup();

        wrapper.DLGTableLayout(8, 6, 0);

        // first row, only the labels for start, stepwidth and end
        wrapper.DLGAddElement(DLGCreateLabel(""));
        wrapper.DLGAddElement(DLGCreateLabel(""));
        wrapper.DLGAddElement(DLGCreateLabel("Start"));
        wrapper.DLGAddElement(DLGCreateLabel("Step"));
        wrapper.DLGAddElement(DLGCreateLabel("End"));
        wrapper.DLGAddElement(DLGCreateLabel(""));
        wrapper.DLGAddElement(DLGCreateLabel(""));
        wrapper.DLGAddElement(DLGCreateLabel(""));

        TagGroup parent_ids = NewTagList();
        row_labels = NewTagList();
        type_selectboxes = NewTagList();
        start_inputboxes = NewTagList();
        step_inputboxes = NewTagList();
        end_inputboxes = NewTagList();
        value_limits = NewTagList();
        swap_upwards_buttons = NewTagList();
        swap_downwards_buttons = NewTagList();

        // add measurement variable rows
        for(number i = 0; i < measurement_variables.TagGroupCountTags(); i++){
            wrapper = self._addSeriesRow(i, wrapper);
        }

        return wrapper;
    }

    TagGroup _createSettingsPanelContent(object self){
        return DLGCreateLabel("Settings Panel");
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
            TagGroup label = DLGCreateLabel(message);
            dialog_items.DLGAddElement(label);
        }

        TagGroup panel_list = DLGCreatePanelList(0);

        TagGroup series_panel = DLGCreatePanel();
        series_panel.DLGAddElement(self._createSeriesPanelContent());
        panel_list.DLGAddPanel(series_panel);

        TagGroup settings_panel = DLGCreatePanel();
        settings_panel.DLGAddElement(self._createSettingsPanelContent());
        panel_list.DLGAddPanel(settings_panel);
        
        dialog_items.DLGAddElement(panel_list);

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
        index_variable_map = NewTagList();
		self.super.init(self._createContent(title, message));

        for(number i = 0; i < measurement_vars.TagGroupCountTags(); i++){
            self.setMeasurementVariableToRow(self._getMeasurementVariableByIndex(i), i);
        }
        
		return self;
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

object dialog = alloc(DMViewDialog).init("Test Dialog", m_vars, "Test Message");

// for(number i = 0; i < m_vars.TagGroupCountTags(); i++){
//     TagGroup v;
//     m_vars.TagGroupGetIndexedTagAsTagGroup(i, v);
//     dialog.setMeasurementVariableToRow(v, i);
// }
if(dialog.pose()){

}