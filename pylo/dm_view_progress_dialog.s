class ProgressDialog : UIFrame{
	string progress_tagname;
	string text_tagname;
	string success_tagname;
	number progress_max;
	number update_task;
	
	number done;
	number cancelled;
	
	TagGroup progress_bar;
	TagGroup progress_label;
	TagGroup textbox;
	
	void cancel(object self){
		cancelled = 1;
		if(!GetPersistentTagGroup().TagGroupDoesTagExist(success_tagname)){
			GetPersistentTagGroup().TagGroupCreateNewLabeledTag(success_tagname);
		}
		GetPersistentTagGroup().TagGroupSetTagAsBoolean(success_tagname, 0);
		self.close();
	}

	void confirm(object self){
		self.close();
	}

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
				
				self.DLGSetProgress("progress_bar", progress / progress_max);
				progress_label.DLGTitle(progress + "/" + progress_max);
			}
			if(GetPersistentTagGroup().TagGroupGetTagAsString(text_tagname, text)){
				self.SetTextElementData("textbox", text)
			}
			self.validateView();
		}
	}
	
    object init(object self, string title, number prog_max, string prog_tagname, string txt_tagname, string succ_tagname){
		progress_tagname = prog_tagname;
		text_tagname = txt_tagname;
		progress_max = prog_max;
		success_tagname = succ_tagname;
		done = 0;
		cancelled = 0;
		
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
		textbox.DLGIdentifier("textbox")
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