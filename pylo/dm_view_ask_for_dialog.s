/**
 * The dialog to ask the user for values.
 */
class DMViewAskForDialog : UIFrame{
    /**
     * The values to ask
     */
    TagGroup values;

    /**
     * The input boxes
     */
    TagGroup inputs;

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
	TagGroup _createContent(object self, string title, string message){
		TagGroup dialog_items;
		TagGroup dialog_tags = DLGCreateDialog(title, dialog_items);
        
        TagGroup label = DLGCreateLabel(message, 130);
        label.DLGHeight(1);
        dialog_items.DLGAddElement(label);

        TagGroup wrapper = DLGCreateGroup();

        inputs = NewTagList();

        // column widths
        number cw1 = 20; // label column
        number cw2 = 40; // value column
        number cw3 = 60; // value column
        
        for(number i = 0; i < values.TagGroupCountTags(); i++){
            TagGroup value_settings;
            values.TagGroupGetIndexedTagAsTagGroup(i, value_settings);

            string description;
            string type;
            string name;
            value_settings.TagGroupGetTagAsString("description", description);
            value_settings.TagGroupGetTagAsString("datatype", type);
            value_settings.TagGroupGetTagAsString("name", name);

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
                input = DLGCreateCheckBox(name, value != 0 ? 1 : 0);
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

            input.DLGIdentifier("input-" + i);

            if(type != "boolean"){
                input.DLGAnchor("North");
                line.DLGAddElement(input);
            }

            inputs.TagGroupInsertTagAsTagGroup(i, input);

            TagGroup description_label = DLGCreateLabel(description, cw3);
            description_label.DLGHeight(ceil(description.len() / 55));
            description_label.DLGAnchor("East");
            line.DLGAddElement(description_label);

            value_wrapper.DLGAddElement(line);
            wrapper.DLGAddElement(value_wrapper);
        }

        dialog_items.DLGAddElement(wrapper);

		return dialog_tags;
    }
	
    /**
     * Create a new dialog.
     *
     * @param title
     *      The title of the dialog
     * @param ask_vals
     *      The values to ask as a `TagList`
     *
     * @return
     *      The dialog
     */
	object init(object self, string title, TagGroup ask_vals, string message){
        values = ask_vals;
		self.super.init(self._createContent(title, message));
        
		return self;
	}

    /**
     * Get the values as a `TagGroup`.
     *
     * @return
     *      The values `TagGroup`
     */
    TagGroup getValues(object self){
        // TagGroup vals = NewTagGroup();
        TagGroup vals = NewTagList();

        for(number i = 0; i < values.TagGroupCountTags(); i++){
            TagGroup input;
            inputs.TagGroupGetIndexedTagAsTagGroup(i, input);

            TagGroup value_settings;
            values.TagGroupGetIndexedTagAsTagGroup(i, value_settings);
            
            // number index = vals.TagGroupCreateNewLabeledTag("" + i);
            number index = i;

            string type;
            value_settings.TagGroupGetTagAsString("datatype", type);

            if(type == "int"){
                number value = input.DLGGetValue();
                // vals.TagGroupSetIndexedTagAsLong(index, value);
                vals.TagGroupInsertTagAsLong(index, value);
            }
            else if(type == "float"){
                number value = input.DLGGetValue();
                // vals.TagGroupSetIndexedTagAsFloat(index, value);
                vals.TagGroupInsertTagAsFloat(index, value);
            }
            else if(type == "boolean"){
                number value = input.DLGGetValue();
                // vals.TagGroupSetIndexedTagAsBoolean(index, value);
                vals.TagGroupInsertTagAsBoolean(index, value);
            }
            else{
                string value = input.DLGGetStringValue();
                // vals.TagGroupSetIndexedTagAsString(index, value);
                vals.TagGroupInsertTagAsString(index, value);
            }
        }

        return vals;
    }
}

object dialog = alloc(DMViewAskForDialog).init("Set values -- PyLo", ask_vals, message);

TagGroup values;

if(dialog.pose()){
    values = dialog.getValues();
}