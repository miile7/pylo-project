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
     * The list of inputboxes for the start values
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
            return 0;
        }
        else{
            return 1;
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
            identifier = identifier.right(p);
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
            // limits += "≥ " + min_value;
        }
        else if(max_value != ""){
            limits += "<= " + max_value;
            // limits += "≤ " + max_value;
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
     *      The measurement variable that is selected or NULL if no measurement variable is selected
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

    void seriesSelectChanged(object self, TagGroup series_select){
        // get the index of the row
        string identifier;
        series_select.DLGGetIdentifier(identifier);
        number index = self.getIdentifierIndex(identifier);

        TagGroup var = self.getSeriesSelectedMeasurementVariable(series_select);

        if(var.TagGroupIsValid()){
            result("Found selected measurement variable for row " + index + ".\n");
            // show the limits
            TagGroup limit_display;
            limit_displays.TagGroupGetIndexedTagAsTagGroup(index, limit_display);
            limit_display.DLGTitle(self._getMeasurementVariableLimits(var));

            // show the start value
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

            // show the step width value
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

            // show the end value
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

            // enable the next series select box if it exists
            if(index + 1 < series_selectboxes.TagGroupCountTags()){
                string name;
                var.TagGroupGetTagAsString("name", name);
                TagGroup on_each_label;
                on_each_labels.TagGroupGetIndexedTagAsTagGroup(index, on_each_label);
                on_each_label.DLGTitle("On each " + name + " point...");

                TagGroup next_series_select;
                series_selectboxes.TagGroupGetIndexedTagAsTagGroup(index + 1, next_series_select);
                next_series_select.DLGEnabled(1);
                if(self.isShown()){
                    // DLGEnabled() does not work if the dialog is shown already
                    string i;
                    next_series_select.DLGGetIdentifier(i);
                    self.setElementIsEnabled(i, 1);
                }

                // clear all items
                TagGroup items;
                next_series_select.TagGroupGetTagAsTagGroup("Items", items);
                items.TagGroupDeleteAllTags();

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

                        string parent_id;
                        parent_var.TagGroupGetTagAsString("unique_id", parent_id);

                        if(parent_id == add_id){
                            // this parent contains this variable already
                            var_selected_in_parent = 1;
                            break;
                        }
                    }

                    if(var_selected_in_parent == 0){
                        // only add if the parent does not contain the variable
                        next_series_select.DLGAddChoiceItemEntry(self._getMeasurementVariableLabel(add_var))
                    }
                }

                if(next_series_select.DLGGetValue() != 0){
                    // the next series has something selected already, trigger the change
                    self.seriesSelectChanged(next_series_select);
                }
            }
        }
        else{
            result("Did NOT find selected variable.\n")
        }
    }

    TagGroup _createSeriesPanelContent(object self){
        TagGroup wrapper = DLGCreateGroup();

        start_value_inputboxes = NewTagList();

        number max_rows = 1;
        TagGroup upper_wrapper = DLGCreateBox("Start parameters");
        upper_wrapper.DLGTableLayout(max_rows * 3, ceil(measurement_variables.TagGroupCountTags() / max_rows), 0);
        upper_wrapper.DLGExpand("X");
        upper_wrapper.DLGFill("X");

        for(number j = 0; j < measurement_variables.TagGroupCountTags(); j++){
            TagGroup var = self._getMeasurementVariableByIndex(j);

            string unique_id;
            var.TagGroupGetTagAsString("unique_id", unique_id);

            string label = self._getMeasurementVariableLabel(var);
            string limits = self._getMeasurementVariableLimits(var);
            if(limits != ""){
                limits = " " + limits;
            }

            // TagGroup label_element = DLGCreateLabel(label, label.len() + 2);
            TagGroup label_element = DLGCreateLabel(label, 20);
            label_element.DLGAnchor("East");
            upper_wrapper.DLGAddElement(label_element);
            
            string start;
            var.TagGroupGetTagAsString("start", start);

            TagGroup start_input = DLGCreateStringField(start, 8);
            start_input.DLGAnchor("West");
            start_input.DLGIdentifier("start_value-" + unique_id);
            start_value_inputboxes.TagGroupInsertTagAsTagGroup(infinity(), start_input);
            upper_wrapper.DLGAddElement(start_input);

            upper_wrapper.DLGAddElement(DLGCreateLabel(limits, 15));
        }

        wrapper.DLGAddElement(upper_wrapper);

        TagGroup lower_wrapper = DLGCreateBox("Series");

        number c = measurement_variables.TagGroupCountTags();
        lower_wrapper.DLGTableLayout(5, c * 2, 0);
        lower_wrapper.DLGExpand("X");
        lower_wrapper.DLGFill("X");

        // header
        lower_wrapper.DLGAddElement(DLGCreateLabel(""));
        lower_wrapper.DLGAddElement(DLGCreateLabel(""));
        lower_wrapper.DLGAddElement(DLGCreateLabel("Start"));
        lower_wrapper.DLGAddElement(DLGCreateLabel("Step width"));
        lower_wrapper.DLGAddElement(DLGCreateLabel("End"));

        // item lists
        series_selectboxes = NewTagList();
        limit_displays = NewTagList();
        start_inputboxes = NewTagList();
        step_inputboxes = NewTagList();
        end_inputboxes = NewTagList();
        on_each_labels = NewTagList();

        // TagGroup first_series_select;

        // add measurement variable rows
        for(number i = 0; i < c ; i++){
            TagGroup series_select = DLGCreateChoice(0, "seriesSelectChanged");
            series_select.DLGExternalPadding(0, i * - 50, 0, 0);
            series_select.DLGWidth(100);
            series_select.DLGAnchor("West");
            series_select.DLGSide("Left");
            if(i > 0){
                series_select.DLGEnabled(0);
                series_select.DLGAddChoiceItemEntry("--");
            }
            else{
                // first_series_select = series_select;
                for(number j = 0; j < measurement_variables.TagGroupCountTags(); j++){
                    TagGroup var = self._getMeasurementVariableByIndex(j);
                    series_select.DLGAddChoiceItemEntry(self._getMeasurementVariableLabel(var))
                }
            }
            series_select.DLGIdentifier("series_variable-" + i);
            series_selectboxes.TagGroupInsertTagAsTagGroup(infinity(), series_select);
            lower_wrapper.DLGAddElement(series_select);

            TagGroup limit_display = DLGCreateLabel("", 10);
            limit_displays.TagGroupInsertTagAsTagGroup(infinity(), limit_display);
            lower_wrapper.DLGAddElement(limit_display);

            TagGroup start_input = DLGCreateStringField("", 8);
            if(i > 0){
                start_input.DLGEnabled(0);
            }
            start_input.DLGIdentifier("series_start-" + i);
            start_inputboxes.TagGroupInsertTagAsTagGroup(infinity(), start_input);
            lower_wrapper.DLGAddElement(start_input);

            TagGroup step_input = DLGCreateStringField("", 8);
            if(i > 0){
                step_input.DLGEnabled(0);
            }
            step_input.DLGIdentifier("series_step-" + i);
            step_inputboxes.TagGroupInsertTagAsTagGroup(infinity(), step_input);
            lower_wrapper.DLGAddElement(step_input);

            TagGroup end_input = DLGCreateStringField("", 8);
            if(i > 0){
                end_input.DLGEnabled(0);
            }
            end_input.DLGIdentifier("series_end-" + i);
            end_inputboxes.TagGroupInsertTagAsTagGroup(infinity(), end_input);
            lower_wrapper.DLGAddElement(end_input);
            
            if(i + 1 < c){
                TagGroup on_each_label = DLGCreateLabel("");
                on_each_label.DLGIdentifier("on_each_label-" + i);
                on_each_labels.TagGroupInsertTagAsTagGroup(infinity(), on_each_label);
                lower_wrapper.DLGAddElement(on_each_label);

                lower_wrapper.DLGAddElement(DLGCreateLabel(""));
                lower_wrapper.DLGAddElement(DLGCreateLabel(""));
                lower_wrapper.DLGAddElement(DLGCreateLabel(""));
                lower_wrapper.DLGAddElement(DLGCreateLabel(""));
            }
            // self.seriesSelectChanged(series_select);
        }

        // trigger changes for all selectboxes, otherwise some functions in the callback do not work,
        // no idea why
        for(number j = 0; j < series_selectboxes.TagGroupCountTags(); j++){
            TagGroup series_select;
            series_selectboxes.TagGroupGetIndexedTagAsTagGroup(j, series_select);
            self.seriesSelectChanged(series_select);
        }

        wrapper.DLGAddElement(lower_wrapper);

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
		self.super.init(self._createContent(title, message));
        
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