import os
import sys
import json
import random
import argparse

if __name__ == "__main__":
    class IOBuffer:
        def __init__(self):
            self.flush()

        def write(self, txt):
            self.buffer += str(txt)
        
        def flush(self):
            self.buffer = ""
        
        def __len__(self):
            return len(self.buffer)
        
        def __str__(self):
            return self.buffer

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    buffer = IOBuffer()
    err_buffer = IOBuffer()

    parser = argparse.ArgumentParser("olcurrent", add_help=True,
                                     description=("Set/get the objectiv lens " +
                                                  "current by using JEOLs " + 
                                                  "PyJEM module."))
    
    # subparsers = parser.add_subparsers(title="Commands", dest="command",
    #                                    required=True)

    # getc_parser = subparsers.add_parser("getc", help=("Get the objectiv lens " + 
    #                                                   "current coarse value"))
    # setc_parser = subparsers.add_parser("setc", help=("Set the objectiv lens " + 
    #                                                   "current coarse value"))
    # setc_parser.add_argument("coarse_value", help=("The objectiv coarse lens " + 
    #                                                "value as an int"), type=int)

    # getf_parser = subparsers.add_parser("getf", help=("Get the objectiv lens " + 
    #                                                   "current fine value"))
    # setf_parser = subparsers.add_parser("setf", help=("Set the objectiv lens " + 
    #                                                   "current fine value"))
    # setf_parser.add_argument("fine_value", help=("The objectiv fine lens " + 
    #                                                "value as an int"), type=int)
                                                  
    parser.add_argument("--getc", help=("Get the objectiv lens current coarse " + 
                                        "value as an integer number"), 
                        action="store_true")
    parser.add_argument("--setc", help=("Set the objectiv lens current coarse " + 
                                        "value as an integer number"),
                        type=int)
    parser.add_argument("--getf", help=("Get the objectiv lens current fine " + 
                                        "value as an integer number"), 
                        action="store_true")
    parser.add_argument("--setf", help=("Set the objectiv lens current fine " + 
                                        "value as an integer number"),
                        type=int)

    parser.add_argument("--output", "-o", help="The output format", 
                        choices=("json", "plain"), default="plain")
    
    parser.add_argument("--keepflc", action="store_true",
                        help=("For controlling the objectiv lens current, the " + 
                              "free lens control must be switched off. If you " + 
                              "do not want this program to switch off the " + 
                              "free lens control automatically, add this switch."))
    parser.add_argument("--restoreflc", action="store_true",
                        help=("If the free lens control is changed, use this " + 
                              "switch to make sure it is changed back to the " + 
                              "original switch state after the program has " + 
                              "executed."))
                        
    debug_group = parser.add_mutually_exclusive_group()
    debug_group.add_argument("--offline", help=("Use the PyJEM offline module " + 
                                                "for testing"),
                             action="store_true")
    
    debug_group.add_argument("--debug", help=("Start with random values. Each " + 
                                         "time the value is set, the new " + 
                                         "value is stored in a file. This " + 
                                         "way a microscope can be 'faked'."),
                             action="store_true")

    args = parser.parse_args()

    sys.stderr = buffer
    sys.stdout = err_buffer

    try:
        if args.debug:
            class FakeLens3:
                def __init__(self):
                    self.values = {}
                    self.path, _ = os.path.splitext(__file__)
                    self.path += ".session"

                    try:
                        with open(self.path, "r") as f:
                            self.values = json.load(f)
                    except (FileNotFoundError, json.decoder.JSONDecodeError):
                        self.values = {}
                    
                    if "flc_info" not in self.values:
                        self.values["flc_info"] = {6: 0, 7: 0}
                        
                    if "getf" not in self.values:
                        self.values["getf"] = random.randint(0, 100)
                    if "getc" not in self.values:
                        self.values["getc"] = random.randint(0, 100)
                
                def save(self):
                    with open(self.path, "w") as f:
                        json.dump(self.values, f)

                def SetOLc(self, value):
                    if self.GetFLCInfo(6):
                        raise IOError(("Cannot set the objective coarse lens " + 
                                       "current because free lens control is " + 
                                       "active."))
                    self.values["getc"] = value
                    self.save()

                def SetOLf(self, value):
                    if self.GetFLCInfo(7):
                        raise IOError(("Cannot set the objective fine lens " + 
                                       "current because free lens control is " + 
                                       "active."))
                    self.values["getf"] = value
                    self.save()

                def GetOLc(self):
                    return self.values["getc"]

                def GetOLf(self):
                    return self.values["getf"]
                
                def GetFLCInfo(self, lens_id):
                    if not str(lens_id) in self.values["flc_info"]:
                        return 0
                    else:
                        return self.values["flc_info"][str(lens_id)]
                    
                def SetFLCSw(self, lens_id, switch):
                    self.values["flc_info"][str(lens_id)] = switch
                    self.save()

            print("Faking some random text", file=old_stdout)
            lens_control = FakeLens3()
        else:
            if args.offline:
                # PyJEM executes some prints so buffer the output
                from PyJEM.offline.TEM3 import Lens3
            else:
                # PyJEM executes some prints so buffer the output
                from PyJEM.TEM3 import Lens3

            lens_control = Lens3()
        
        # lens_ids = {
        #   0: "CL1",
        # 	1: "CL2",
        # 	2: "CL3",
        # 	3: "CM",
        # 	4: "reserve",
        # 	5: "reserve",
        # 	6: "OL Coarse",
        # 	7: "OL Fine",
        #   8: "OM1",
        # 	9: "OM2",
        # 	10: "IL1",
        # 	11: "IL2",
        # 	12: "IL3",
        # 	13: "IL4",
        # 	14: "PL1",
        # 	15: "PL2",
        # 	16: "PL3",
        # 	17: "reserve",
        #   18: "reserve",
        # 	19: "FLCoarse",
        # 	20: "FLFine",
        # 	21: "FLRatio",
        # 	22: "reserve",
        # 	23: "reserve",
        # 	24: "reserve",
        # 	25: "reserve",
        # }
        # free lens control status for each lens
        lens_flc_status_changes = []
        needed_lens_ids = [6, 7]

        if not args.keepflc:
            for lens_id in needed_lens_ids:
                flc_is_on = lens_control.GetFLCInfo(lens_id)
                if isinstance(flc_is_on, (tuple, list)):
                    # fixing but of Lens3 offline
                    flc_is_on = flc_is_on[0]
                
                if flc_is_on:
                    # free lens control is on
                    # save lens to set it back to the previous state after execution
                    lens_flc_status_changes.append(lens_id)
                    # switch it off
                    lens_control.SetFLCSw(lens_id, 0)

        output = {}
        
        if args.setc is not None:
            lens_control.SetOLc(int(args.setc))
        if args.setf is not None:
            lens_control.SetOLf(int(args.setf))
        
        if args.setc is not None or args.getc:
            output["getc"] = lens_control.GetOLc()
        if args.setf is not None or args.getf:
            output["getf"] = lens_control.GetOLf()
        
        if args.setc is None and not args.getc and args.setf is None and not args.setc:
            raise RuntimeError("Nothing to do")
            
        if args.offline or args:
            # fix bug in PyJEM offline
            for key, val in output.items():
                if isinstance(val, (list, tuple)):
                    output[key] = val[-1]
        
        if args.restoreflc:
            # switch back to the initial state
            for lens_id in lens_flc_status_changes:
                # switch it on again
                lens_control.SetFLCSw(lens_id, 1)
    finally:
        sys.stderr = old_stderr
        sys.stdout = old_stdout

    if args.output == "plain":
        print(buffer)

        if len(err_buffer) > 0:
            print(err_buffer)
            parser.print_help()
            sys.exit(1)
        else:
            for key, val in output.items():
                print("{}: {}".format(key, val))
            sys.exit(0)
    else:
        if len(err_buffer) > 0:
            json.dump({"buffer": str(buffer), "error": str(err_buffer)}, fp=sys.stdout)
            sys.exit(1)
        else:
            json.dump({"output": output, "buffer": str(buffer)}, fp=sys.stdout)
            sys.exit(0)
