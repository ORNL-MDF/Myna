"""Define loading of the beam spot size in millimeters from databases

NOTE: There are many definitions of the beam spot size that can be used,
such as D4sigma, 1/e^2, and FWHM. Currently, myna will not enforce a
particular definition, though the D4sigma spot size is preferred when
applicable.
"""

from .data import *
from .database_types import *


class SpotSize(PartMetadata):
    """BuildMetadata subclass for the beam spot size (float value, units = mm)

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, build, part):
        PartMetadata.__init__(self, datatype, build, part)
        self.unit = "mm"
        self.value = self.value_from_file()

    def value_from_file(self):
        """Returns the beam spot size (diameter) in millimeters from the associated
        file

        Returns: float
        """
        data = self.load_file_data()
        value = None
        if self.datatype == PeregrineDB:
            index = [
                ind
                for ind, x in enumerate(data["parameter_names"])
                if x == "Spot Size (mm)"
            ][0]
            value = float(data["parameter_values"][index])

            # NOTE: Correct for bug in Peregrine that saved spot size as microns
            # in some files. Assume that if the spot size is greater than 10
            # that it is stored in microns and correct accordingly.
            if value > 10:
                value = value * 1e-3

        return value
