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
        
        def __str__(self):
            return self.buffer

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    buffer = IOBuffer()

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
    sys.stdout = buffer
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
                    
                if "getf" not in self.values:
                    self.values["getf"] = random.randint(0, 100)
                if "getc" not in self.values:
                    self.values["getc"] = random.randint(0, 100)
            
            def save(self):
                with open(self.path, "w") as f:
                    json.dump(self.values, f)

            def SetOLc(self, value):
                self.values["getc"] = value
                self.save()

            def SetOLf(self, value):
                self.values["getf"] = value
                self.save()

            def GetOLc(self):
                return self.values["getc"]

            def GetOLf(self):
                return self.values["getf"]
        
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
    
    output = {}
    error = None
    
    if args.setc is not None:
        lens_control.SetOLc(int(args.setc))
    if args.setf is not None:
        lens_control.SetOLf(int(args.setf))
    
    if args.setc is not None or args.getc:
        output["getc"] = lens_control.GetOLc()
    if args.setf is not None or args.getf:
        output["getf"] = lens_control.GetOLf()
    
    if args.setc is None and not args.getc and args.setf is None and not args.setc:
        error = "Nothing to do"
        
    if args.offline:
        # fix bug in PyJEM offline
        for key, val in output.items():
            if isinstance(val, (list, tuple)):
                output[key] = val[-1]

    sys.stderro = old_stderr
    sys.stdout = old_stdout

    if args.output == "plain":
        print(buffer)

        if error is not None:
            print(error, "\n")
            parser.print_help()
            sys.exit(1)
        else:
            for key, val in output.items():
                print("{}: {}".format(key, val))
            sys.exit(0)
    else:
        if error is not None:
            json.dump({"buffer": str(buffer), "error": error}, fp=sys.stdout)
            sys.exit(1)
        else:
            json.dump({"output": output, "buffer": str(buffer)}, fp=sys.stdout)
            sys.exit(0)
