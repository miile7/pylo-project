import pylo
import pylo.config

pylo.config.VIEW = pylo.CLIView()
pylo.config.CONFIGURATION = pylo.IniConfiguration()

pylo.execute()