'''Data subclass for spot size'''
import os
import numpy as np
from .data import *

class PeregrineSpotSize(PeregrinePartData):
    
    def __init__(self, build, part):
        PeregrinePartData.__init__(self, build, part)
        self.file = os.path.join(self.build, "Peregrine", "simulation", part, "part.npz")
        self.unit = "mm"
        self.value = self.value_from_file()

    def load_file_data(self):
        data = np.load(self.file, allow_pickle=True)
        return data
        
    def value_from_file(self):
        data = self.load_file_data()
        index = [ind for ind, x in enumerate(data['parameter_names']) if x == 'Spot Size (mm)'][0]
        value = data['parameter_values'][index]
        return value