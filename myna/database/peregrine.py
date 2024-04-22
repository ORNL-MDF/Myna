"""Database class for an ORNL MDF Peregrine build's file structure"""

from myna.core.db import Database
from myna.core import metadata
import os
import numpy as np


class PeregrineDB(Database):
    def __init__(self):
        Database.__init__(self)
        self.description = "ORNL MDF Peregrine build file structure"

    def load(metadata_obj, build, part=None, layer=None):
        """Load and return a metadata value from the database

        Implemented metadata loaders:
        - LaserPower
        - LayerThickness
        - Material
        - Preheat
        - SpotSize
        - STL
        - Scanpath
        """

        if type(metadata_obj) == metadata.LaserPower:
            datafile = os.path.join(build, "Peregrine", "simulation", part, "part.npz")
            data = np.load(datafile, allow_pickle=True)
            index = [
                ind for ind, x in enumerate(data["parameter_names"]) if x == "Power (W)"
            ][0]
            return float(data["parameter_values"][index])

        elif type(metadata_obj) == metadata.LayerThickness:
            datafile = os.path.join(build, "Peregrine", "simulation", "buildmeta.npz")
            data = np.load(datafile, allow_pickle=True)
            conversion = 1e-3  # millimeters -> meters
            return float(data["layer_thickness"] * conversion)

        elif type(metadata_obj) == metadata.Material:
            datafile = os.path.join(build, "Peregrine", "simulation", "buildmeta.npz")
            data = np.load(datafile, allow_pickle=True)
            return str(data["material"])

        elif type(metadata_obj) == metadata.Preheat:
            datafile = os.path.join(build, "Peregrine", "simulation", "buildmeta.npz")
            data = np.load(datafile, allow_pickle=True)
            index = [
                ind
                for ind, x in enumerate(data["metadata_names"])
                if x == "Target Preheat (°C)"
            ][0]
            return float(data["metadata_values"][index]) + 273.15

        elif type(metadata_obj) == metadata.SpotSize:
            datafile = os.path.join(build, "Peregrine", "simulation", part, "part.npz")
            data = np.load(datafile, allow_pickle=True)
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

        elif type(metadata_obj) == metadata.STL:
            file_database = os.path.join(
                build, "Peregrine", "simulation", part, f"part.stl"
            )
            return file_database

        elif type(metadata_obj) == metadata.Scanpath:
            file_database = os.path.join(
                build, "Peregrine", "simulation", part, f"{int(layer):07d}.txt"
            )
            return file_database

        else:
            print(f"Error loading: {type(metadata_obj)}")
            raise NotImplementedError
