import DigitalMicrograph as DM

try:
	DM.ClearResults()
	close_tag_name = "__pylo_close_loading_dialog"
	# show waiting dialog
	script = "\n".join((
		"GetPersistentTagGroup().TagGroupDeleteTagWithLabel(\"{}\");".format(close_tag_name),
		"class LoadDialog : UIFrame{",
			"number update_task;",
			"",
			"void checkForClose(object self){",
				"if(GetPersistentTagGroup().TagGroupDoesTagExist(\"{}\")){{".format(close_tag_name),
					"GetPersistentTagGroup().TagGroupDeleteTagWithLabel(\"{}\");".format(close_tag_name),
					"RemoveMainThreadTask(update_task);",
					"self.close();",
				"}",
			"}",
			"",
			"object init(object self){",
				"TagGroup dlg, dlg_items, text;",
				"",
				"dlg = DLGCreateDialog(\"Loading...\", dlg_items);",
				"dlg_items.DLGAddElement(DLGCreateLabel(\"\\n          Loading... This can take a while.          \\n\"));",
				"",
				"update_task = AddMainThreadPeriodicTask(self, \"checkForClose\", 0.1);",
				"",
				"self.super.init(dlg);",
				"return self;",
			"}",
		"}",
		"alloc(LoadDialog).init().display(\"Loading...\");"
	))
	DM.ExecuteScriptString(script)

	print("Starting, this can take a while...")
	print("")

	print("Initializing DigitalMicrograph environmnet...")

	# the name of the tag is used, this is deleted so it shouldn't matter anyway
	file_tag_name = "__pylo_python__file__"
	# the dm-script to execute, double curly brackets are used because of the 
	# python format function
	script = ("\n".join((
		"DocumentWindow win = GetDocumentWindow(0);",
		"if(win.WindowIsvalid()){{",
			"if(win.WindowIsLinkedToFile()){{",
				"TagGroup tg = GetPersistentTagGroup();",
				"if(!tg.TagGroupDoesTagExist(\"{tag_name}\")){{",
					"number index = tg.TagGroupCreateNewLabeledTag(\"{tag_name}\");",
					"tg.TagGroupSetIndexedTagAsString(index, win.WindowGetCurrentFile());",
				"}}",
				"else{{",
					"tg.TagGroupSetTagAsString(\"{tag_name}\", win.WindowGetCurrentFile());",
				"}}",
			"}}",
		"}}"
	))).format(tag_name=file_tag_name)

	# execute the dm script
	DM.ExecuteScriptString(script)

	# read from the global tags to get the value to the python script
	if DM.GetPersistentTagGroup():
		s, __file__ = DM.GetPersistentTagGroup().GetTagAsString(file_tag_name);
		if s:
			# delete the created tag again
			DM.GetPersistentTagGroup().DeleteTagWithLabel(file_tag_name)
		else:
			del __file__

	try:
		__file__
	except NameError:
		# set a default if the __file__ could not be received
		__file__ = ""

	import os
	if __file__ != "":
		import sys
		
		base_path = str(os.path.dirname(__file__))
		
		if base_path not in sys.path:
			sys.path.insert(0, base_path)

	print("Initializing python environment...")

	import pylo

	print("Preparing...")
	# pylo.OFFLINE_MODE = True

	# adding device paths
	# get device paths from dm-script and save them into global tags
	application_dir_names = ("application", "preference", "plugin")
	dir_path_tag_name = "__pylo_dir_path_{dirname}"
	dmscript_template = "\n".join((
		"if(!GetPersistentTagGroup().TagGroupDoesTagExist(\"{tagname}\")){{",
			"GetPersistentTagGroup().TagGroupCreateNewLabeledTag(\"{tagname}\");",
		"}}",
		"GetPersistentTagGroup().TagGroupSetTagAsString(\"{tagname}\", GetApplicationDirectory(\"{dirname}\", 0));"
	))
	# create the script
	dmscript = []
	for name in application_dir_names:
		dmscript.append(dmscript_template.format(tagname=dir_path_tag_name.format(dirname=name),
												 dirname=name))
	# execute the script
	DM.ExecuteScriptString("\n".join(dmscript))
	# read the values from the global tags
	for name in application_dir_names:
		tn = dir_path_tag_name.format(dirname=name)
		s, dir_path = DM.GetPersistentTagGroup().GetTagAsString(tn)
		if s and os.path.exists(dir_path):
			ini_path = os.path.realpath(os.path.join(dir_path, "devices.ini"))
			if os.path.exists(ini_path) and os.path.isfile(ini_path):
				# add the values to the ini loader
				pylo.loader.device_ini_files.append(ini_path)
		DM.GetPersistentTagGroup().DeleteTagWithLabel(tn)
	
	if len(pylo.loader.device_ini_files) > 0:
		print("Found device files:")
		for f in pylo.loader.device_ini_files:
			print("  ", f)
	else:
		print("Did not find any device files (devices.ini)")

	# create view and configuration, both using the DM environmnent
	view = pylo.DMView()
	configuration = pylo.DMConfiguration()

	# remove loading dialog, dialog deletes tag
	DM.GetPersistentTagGroup().SetTagAsBoolean(close_tag_name, True)

	print("Done.")
	print("Starting...")

	# redirect all print() calls to the debug window
	DM.SetOutputTo(2)
	pylo.execute(view, configuration)
	# set everything back to the results window
	DM.SetOutputTo(0)

	print("Done with everything.")
	print("Exiting.")
except Exception as e:
	# dm-script error messages are very bad, use this for getting the error 
	# text and the correct traceback
	print("{}: ".format(e.__class__.__name__), e)
	import traceback
	traceback.print_exc()