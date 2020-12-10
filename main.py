import pylo

pylo.config.VIEW = pylo.CLIView()
pylo.config.CONFIGURATION = pylo.IniConfiguration()

pylo.execute(pylo.config.VIEW, pylo.config.CONFIGURATION)