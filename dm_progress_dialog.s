class TagUpdateThread : Thread{
	number running;
	string text;
	
	object init(object self){
		running = 1;
		text = "";
		return self;
	}
	
	void RunThread(object self){
		if(!GetPersistentTagGroup().TagGroupDoesTagExist("__progress_dialog_progress")){
			number index = GetPersistentTagGroup().TagGroupCreateNewLabeledTag("__progress_dialog_progress");
			GetPersistentTagGroup().TagGroupSetIndexedTagAsNumber(index, 0);
		}
		if(!GetPersistentTagGroup().TagGroupDoesTagExist("__progress_dialog_text")){
			number index = GetPersistentTagGroup().TagGroupCreateNewLabeledTag("__progress_dialog_text");
			GetPersistentTagGroup().TagGroupSetIndexedTagAsString(index, "");
		}

		sleep(0.3);
		
		number progress = 1;
		number counter = 1;
		while(running && counter < 50 && progress <= 1000){
			progress = counter * counter;
			if(progress >= 1000){
				progress = 1000;
				running = 0;
			}
			text += "Step " + counter + ", progress is now " + progress + ".\n";
			GetPersistentTagGroup().TagGroupSetTagAsNumber("__progress_dialog_progress", progress);
			GetPersistentTagGroup().TagGroupSetTagAsString("__progress_dialog_text", text);
			counter += 1;
			sleep(0.3);
		}
	}
	
	void stopThread(object self){
		running = 0;
	}
}

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

alloc(TagUpdateThread).init().startThread()
alloc(ProgressDialog).init("Title", 964, "__progress_dialog_progress", "__progress_dialog_text").pose()