'''Data subclass for build plate preheat'''
import os
import numpy as np
from .data import *

class PeregrinePreheat(PeregrineBuildData):
    
    def __init__(self, build):
        PeregrineBuildData.__init__(self, build)
        self.file = os.path.join(self.build, "Peregrine", "simulation", "buildmeta.npz")
        self.unit = "K"
        self.value = self.value_from_file()

    def load_file_data(self):
        data = np.load(self.file, allow_pickle=True)
        return data
        
    def value_from_file(self):
        data = self.load_file_data()
        index = [ind for ind, x in enumerate(data['metadata_names']) if x == 'Target Preheat (°C)'][0]
        value = float(data['metadata_values'][index]) + 273.15
        return value

        
    