import os
import sys
import datetime
import matplotlib.pyplot as plt
from PIL import Image as PILImage
from mini_cli import input_yn, input_confirm, input_int, input_filesave, input_text

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

if (__name__ == "__main__" and 
    input_yn("Is the microscope attatched to the computer?")):
    from PyJEM.TEM3 import Lens3
    from PyJEM.TEM3 import Stage3
    from PyJEM.TEM3 import EOS3
    from PyJEM.detector import Detector
    from PyJEM.detector.function import get_attached_detector
    offline_mode = False
else:
    from PyJEM.offline.TEM3.lens3 import Lens3
    from PyJEM.offline.TEM3.stage3 import Stage3
    from PyJEM.offline.TEM3.eos3 import EOS3
    from PyJEM.offline.detector import Detector
    from PyJEM.offline.detector.function import get_attached_detector
    offline_mode = True

    print("Using offline mode, values are protocolled:\n")

version = 1
lense_control = Lens3()
stage = Stage3()
eos = EOS3()

OL_COARSE_LENSE_ID = 6
OL_FINE_LENSE_ID = 7
success_log = []

def check_free_lense_control():
    lense_control.SetFLCSw(OL_FINE_LENSE_ID, 1)
    lense_control.SetFLCSw(OL_COARSE_LENSE_ID, 1)

    if offline_mode:
        print("OL Fine:", lense_control.flc_info[OL_FINE_LENSE_ID])
        print("OL Coarse:", lense_control.flc_info[OL_COARSE_LENSE_ID])

def check_ol_fine(value):
    lense_control.SetOLf(value)

    if offline_mode:
        print("OL Fine:", lense_control.flc_info[OL_FINE_LENSE_ID])

def check_ol_coarse(value):
    lense_control.SetOLc(value)

    if offline_mode:
        print("OL Coarse:", lense_control.flc_info[OL_COARSE_LENSE_ID])

def check_x_tilt(value):
    stage.SetTiltXAngle(value)

    if offline_mode:
        print("X tilt:", stage.position[3])

def check_focus(value):
    raise NotImplementedError("Which focus to use?")

    eos.SetObjFocus(value)
    eos.SetDiffFocus(value) # +-1 to 50
    lense_control.SetDiffFocus(value) # +-1 to 50
    lense_control.SetILFocus(value)
    lense_control.SetPLFocus(value)

    if offline_mode:
        print("object focus:", eos.objfocus)

def check_image(detector_name):
    detector = Detector(detector_name)
    
    image_data = detector.snapshot_rawdata()
    image = PILImage.frombytes('L', (1024,1024), image_data, 'raw')
    plt.imshow(image)
    plt.show()

def log(txt, success):
    success_log.append((txt, success))

tests = (
    ("yn",
     "Switching objective lenses (fine and coarse) to use free lense control",
     "Switch free lense control for objective lense",
     "Are the (fine and coarse) objective lenses in free lense control mode?",
     check_free_lense_control),
    ("int",
     "Set the objective lense FINE current to the given value.",
     "Set objective lense fine",
     "Is the objective lense fine current equal to the input value?",
     check_ol_fine),
    ("int",
     "Set the objective lense COARSE current to the given value.",
     "Set objective lense coarse",
     "Is the objective lense coarse current equal to the input value?",
     check_ol_coarse),
    ("int",
     "Set the x tilt to the given value.",
     "Set x tilt",
     "Is the x tilt equal to the input value?",
     check_x_tilt),
    ("str",
     "Record an image with the given detector. Possible detectors are: {}".format(
        ", ".join(map(lambda  x: "'{}'".format(x), get_attached_detector()))
     ),
     "Set Detector",
     "Was a valid image shown?",
     check_image),
    ("int",
     "Set the focus to the given value.",
     "Set focus",
     "Is the focus set correctly to the given value?",
     check_focus)
)

if __name__ == "__main__":
    for box, descr, short, confirm, test in tests:
        val = None
        if box == "yn":
            do_test = input_confirm(descr, short)
        elif box == "int":
            val = input_int(descr, short)

            do_test = val is not None
        elif box == "str":
            val = input_text(descr, short)

            do_test = val is not None
        
        if do_test:
            if val is not None:
                test(val)
            else:
                test()

            log(
                short,
                input_yn(confirm, "Did it work?")
            )
        else:
            break
    
    l = max([len(t[1]) for t in tests])
    tl = l + 2 + max(len("True"), len("False"))

    out = ""
    out += "Test results ({:%Y-%m-%d %H:%M:%S} - v{:0.1f})\n".format(datetime.datetime.now(), version)
    out += "=" * tl + "\n"
    for i, (text, success) in enumerate(success_log):
        out += ("{:" + str(l) + "} {}\n").format(text + ":", success)
        out += "-" * tl + "\n"
    
    if offline_mode:
        print("\n")
    
    print(out)
    fn = input_filesave("Save the log", "Save log", "pyjem-test.log", ".log;.txt")

    if fn != None:
        with open(fn, "w+") as f:
            f.write(out)
            print("Wrote log to {}.".format(fn))