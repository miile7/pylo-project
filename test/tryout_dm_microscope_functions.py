import DigitalMicrograph as DM

dm_microscope = DM.Py_Microscope()

dm_microscope.SetStageAlpha(5)
# dm_microscope.SetStageBeta(5)

dm_microscope.SetFocus(3)
dm_microscope.SetCalibratedFocus(3)

dm_microscope.SetBeamBlanked(True)