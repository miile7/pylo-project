if __name__ == "__main__":
    import os
    import sys
    import argparse

    try:
        p = os.path.dirname(__file__)
        if p not in sys.path:
            sys.path.append(p)
    except NameError:
        pass
    
    try:
        pylo = sys.modules["pylo"]
    except KeyError as e:
        raise RuntimeError("Please use 'python -m pylo' to start PyLo") from e
    
    from pylo import execute
    from pylo import CLIView
    from pylo import StopProgram
    from pylo import IniConfiguration
    from pylo.config import PROGRAM_NAME
    from pylo.pylolib import getDeviceText
    from pylo.pylolib import defineConfigurationOptions

    parser = argparse.ArgumentParser(PROGRAM_NAME, 
                                     description="Record lorentz-TEM images")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-s", "--settings", help="Show the settings", 
                       action="store_true")
    group.add_argument("-d", "--devices", 
                       help="Show the directories and the device.ini files",
                       action="store_true")
    group.add_argument("-r", "--reset", help="Reset the settings", 
                       action="store_true")

    program_args = parser.parse_args()

    view = CLIView()
    configuration = IniConfiguration()

    try:
        if program_args.settings:
            defineConfigurationOptions(configuration)
            view.showSettings(configuration)
        elif program_args.devices:
            view.showHint(getDeviceText())
        elif program_args.reset:
            configuration.reset()
            print("Configuration is reset.")
        else:
            # execute pylo if it is run as a program
            execute(view, configuration)
    except StopProgram:
        print("Exiting.")