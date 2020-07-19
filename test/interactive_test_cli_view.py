import os
import sys
sys.path.append(os.path.abspath("."))

import pylo
import pylo.config

pylo.config.CONFIGURATION = pylo.AbstractConfiguration()
pylo.config.VIEW = pylo.CLIView()

controller = pylo.Controller()
controller.startProgramLoop()
controller.waitForProgram()