class Measurement:
    def init(self, *series):
        self.series = series

    async def start(self):
        pass

    async def _recordImage(self, series):
        pass

    async def stop(self):
        pass

class MeasurementProperty:
    # name
    # min_possible_value
    # max_possible_value
    # setter # callback function in Microscope class
    # getter # callback function in Microscope class
    pass

class MeasurementSeries:
    # property
    # start
    # end
    # step_width
    # on_each_point
    pass

def start_series(series):
    pass