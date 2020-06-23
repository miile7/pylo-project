import typing

class MeasurementSeries:
    """This class represents a measurement series.

    The measurement series is the series that will hold the definition of the 
    measurement. It contains each single point (with all the possible 
    variables) and their state. If all states are visited, the measurement is 
    done.

    Attributes
    ----------
    tags : dict, optional
        Any additional information that should be stored for this measurement
        series
    steps : list of dicts
        A list that contains all the steps to make as dicts, each dict 
        contains the unique_ids of each MeasurementVariable as the key, the 
        value is the corresponding value
    """

    def __init__(self, steps: typing.List[dict], tags: typing.Optional[dict]=None):
        self.steps = steps
        self.tags = tags