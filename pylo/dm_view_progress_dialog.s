class ProgressDialog : UIFrame{
	string progress_tagname;
	string text_tagname;
	number progress_max;
	number update_task;
	
	number done;
	
	TagGroup progress_bar;
	TagGroup progress_label;
	TagGroup textbox;
	
	void updateDialog(object self){
		number progress;
		string text;
		
		if(GetPersistentTagGroup().TagGroupDoesTagExist(progress_tagname)){
			if(GetPersistentTagGroup().TagGroupGetTagAsNumber(progress_tagname, progress)){
				if(progress < 0){
					progress = 0;
				}
				else if(progress >= progress_max){
					progress = progress_max;
					done = 1;
					RemoveMainThreadTask(update_task);
				}
				
				self.DLGSetProgress("progress_bar", progress / progress_max);
				progress_label.DLGTitle(progress + "/" + progress_max);
			}
			if(GetPersistentTagGroup().TagGroupGetTagAsString(text_tagname, text)){
				textbox.DLGLabel(text);
				textbox.DLGInvalid(1);
			}
			self.validateView();
		}
	}
	
    object init(object self, string title, number prog_max, string prog_tagname, string txt_tagname){
		progress_tagname = prog_tagname;
		text_tagname = txt_tagname;
		progress_max = prog_max
		done = 0;
		
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
        dialog_items.DLGAddElement(textbox);
        
		if(GetPersistentTagGroup().TagGroupDoesTagExist(progress_tagname)){
			GetPersistentTagGroup().TagGroupSetTagAsNumber(progress_tagname, 0);
		}
		if(GetPersistentTagGroup().TagGroupDoesTagExist(text_tagname)){
			GetPersistentTagGroup().TagGroupSetTagAsString(text_tagname, "");
		}
        
        update_task = AddMainThreadPeriodicTask(self, "updateDialog", 0.1)
        
        self.super.init(dialog);
        return self;
    }
    
    number pose(object self){
		if(self.super.pose() == 1){
			if(!done){
				self.pose()
			}
			else{
				RemoveMainThreadTask(update_task);
				return 1;
			}
		}
		else{
			RemoveMainThreadTask(update_task);
			return 0;
		}
    }
}

string title = "Measuring -- PyLo"
// number max_progress = 100;
// string progress_tn = "__progress_dialog_progress"
// string text_tn = "__progress_dialog_text"

// number success;
// success = alloc(ProgressDialog).init(title, max_progress, progress_tn, text_tn).pose();