/**
 * The dialog to show that the measurement is running and to let the user know what exactly is 
 * happening at the moment.
 */
class ProgressDialog : UIFrame{
	/**
	 * The tagname in the persistent tags where the progress is saved to.
	 */
	string progress_tagname;

	/**
	 * The tagname in the persistent tags where the value of the text field is saved to.
	 */
	string text_tagname;

	/**
	 * The taganme in the persistent tags where the success value should be saved to.
	 */
	string success_tagname;

	/**
	 * The number the progress can be at the maximum
	 */
	number progress_max;

	/**
	 * The progress of the last time before updating
	 */
	number last_progress;

	/**
	 * The id of the task that observes the tags to get the last value
	 */
	number update_task;
	
	/**
	 * Whether the progress is done, this is 1 as soon as the progress is equal to the progress max
	 */
	number done;

	/**
	 * Whether the cancel button was clicked or not
	 */
	number cancelled;
	
	/**
	 * The progress bar `TagGroup` object
	 */
	TagGroup progress_bar;
	
	/**
	 * The progress display `TagGroup` object
	 */
	TagGroup progress_label;
	
	/**
	 * The text box `TagGroup` object
	 */
	TagGroup textbox;
	
	/**
	 * The callback function when the cancel button is clicked.
	 *
	 * This sets the success in the persistent tags to 0 and closes the dialog.
	 */
	void cancel(object self){
		cancelled = 1;
		if(!GetPersistentTagGroup().TagGroupDoesTagExist(success_tagname)){
			GetPersistentTagGroup().TagGroupCreateNewLabeledTag(success_tagname);
		}
		GetPersistentTagGroup().TagGroupSetTagAsBoolean(success_tagname, 0);
		self.close();
	}

	/**
	 * The callback function when the ok button is clicked.
	 *
	 * This closes the dialog
	 */
	void confirm(object self){
		self.close();
	}

	/**
	 * Sets the progress to be finished.
	 */
	void _done(object self){
		if(cancelled){
			return;
		}

		if(!GetPersistentTagGroup().TagGroupDoesTagExist(success_tagname)){
			GetPersistentTagGroup().TagGroupCreateNewLabeledTag(success_tagname);
		}
		GetPersistentTagGroup().TagGroupSetTagAsBoolean(success_tagname, 1);
		done = 1;
		RemoveMainThreadTask(update_task);

		self.SetElementIsEnabled("ok_button", 1);
		self.SetElementIsEnabled("cancel_button", 0);
	}
	
	/**
	 * The update function that is executed in a periodic interval. This checks the current progress
	 * and the text content in the persistent tags and applies the values to the displayed elements.
	 * When the progress is equal to the `DMViewProgressDialog::progress_max` it executes the 
	 * `DMViewProgressDialog::done()` function
	 */
	void updateDialog(object self){
		number progress;
		string text;

		if(cancelled){
			return;
		}
		
		if(GetPersistentTagGroup().TagGroupDoesTagExist(progress_tagname)){
			if(GetPersistentTagGroup().TagGroupGetTagAsNumber(progress_tagname, progress)){
				if(progress < 0){
					progress = 0;
				}
				else if(progress >= progress_max){
					progress = progress_max;
					self._done();
				}
				
				// check if the dialog is initialized already, if not the progress_bar does not 
				// exist and DLGSetProgress() will raise an error which warns that the element
				// does not exist which will crash the dialog, note that this function is started 
				// before the dialog is initialized
				TagGroup p = self.lookupElement("progress_bar");
				if(p.TagGroupIsValid()){
					// if(floor(progress) == last_progress){
					// 	// fake some progress, otherwise the textbox does not update
					// 	number x = progress - floor(progress) + 0.5
					// 	progress = floor(progress) + 0.5 - 1/x;
					// }
					self.DLGSetProgress("progress_bar", progress / progress_max);
					progress_label.DLGTitle(floor(progress) + "/" + progress_max);
					last_progress = progress
				}
			}
			if(GetPersistentTagGroup().TagGroupGetTagAsString(text_tagname, text)){
				// check if the dialog is initialized already, if not the textbox does not 
				// exist and SetTextElementData() will raise an error which warns that the element
				// does not exist which will crash the dialog, note that this function is started 
				// before the dialog is initialized
				TagGroup t = self.lookupElement("textbox");
				if(t.TagGroupIsValid()){
					self.SetTextElementData("textbox", text);
					t.DLGInvalid(1);
				}
			}
			self.validateView();
		}
	}
	
	/**
	 * Initialize the dialog.
	 *
	 * @param title
	 *		The title to display in the top bar
	 * @param prog_max
	 *		The maximum number the progress can be
	 * @param prog_tagname
	 * 		The tagname in the persistent tags where the current progress is saved to
	 * @param txt_tagname
	 *		The tagname in the persistent tags where the text to show in the textbox is saved to
	 * @param succ_tagname
	 *		The tagname in the persistent tags were to save the success value to if the user 
	 *		interacts with the dialog
	 */
    object init(object self, string title, number prog_max, string prog_tagname, string txt_tagname, string succ_tagname){
		progress_tagname = prog_tagname;
		text_tagname = txt_tagname;
		progress_max = prog_max;
		success_tagname = succ_tagname;
		done = 0;
		cancelled = 0;
		last_progress = 0;
		
        TagGroup dialog_items;
        TagGroup dialog = DLGCreateDialog(title, dialog_items);
        
        TagGroup progress_group = DLGCreateGroup();
        progress_group.DLGTableLayout(2, 1, 0);
		progress_group.DLGFill("X");
		progress_group.DLGWidth(100);
		
        progress_bar = DLGCreateProgressBar("progress_bar");  
		progress_bar.DLGAnchor("West");
		progress_bar.DLGFill("X");   
		progress_bar.DLGInternalpadding(250, 0);
        progress_group.DLGAddElement(progress_bar);
        
        progress_label = DLGCreateLabel("0/" + progress_max);  
		progress_label.DLGAnchor("West");
		progress_label.DLGFill("X");
		progress_label.DLGWidth(20);
        progress_group.DLGAddElement(progress_label);
        
        dialog_items.DLGAddElement(progress_group);
        
        textbox = DLGCreateTextBox(100, 10, 65535);
		textbox.DLGIdentifier("textbox");
        dialog_items.DLGAddElement(textbox);
        
		if(GetPersistentTagGroup().TagGroupDoesTagExist(progress_tagname)){
			GetPersistentTagGroup().TagGroupSetTagAsNumber(progress_tagname, 0);
		}
		if(GetPersistentTagGroup().TagGroupDoesTagExist(text_tagname)){
			GetPersistentTagGroup().TagGroupSetTagAsString(text_tagname, "");
		}
		
		TagGroup button_wrapper = DLGCreateGroup();
		button_wrapper.DLGTableLayout(2, 1, 0);

		TagGroup ok_button = DLGCreatePushButton("Ok", "confirm");
		ok_button.DLGAnchor("East");
		ok_button.DLGEnabled(0);
		ok_button.DLGIdentifier("ok_button");
		button_wrapper.DLGAddElement(ok_button);

		TagGroup cancel_button = DLGCreatePushButton("Cancel", "cancel");
		cancel_button.DLGAnchor("East");
		cancel_button.DLGIdentifier("cancel_button");
		button_wrapper.DLGAddElement(cancel_button);

		dialog_items.DLGAddElement(button_wrapper);
        
        update_task = AddMainThreadPeriodicTask(self, "updateDialog", 0.1);
        
        self.super.init(dialog);
        return self;
    }
}

string title = "Measuring -- PyLo"
// number max_progress = 100;
// string progress_tn = "__progress_dialog_progress"
// string text_tn = "__progress_dialog_text"
// string success_tn = "__progress_dialog_success"

// alloc(ProgressDialog).init(title, max_progress, progress_tn, text_tn, success_tn).display(title);