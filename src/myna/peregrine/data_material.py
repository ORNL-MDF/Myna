'''Data subclass for material name'''
import os
import numpy as np
from .data import *

class PeregrineMaterial(PeregrineBuildData):
    
    def __init__(self, build):
        PeregrineBuildData.__init__(self, build)
        self.file = os.path.join(self.build, "Peregrine", "simulation", "buildmeta.npz")
        self.value = self.value_from_file()

    def load_file_data(self):
        data = np.load(self.file, allow_pickle=True)
        return data
        
    def value_from_file(self):
        data = self.load_file_data()
        value = self.material_map(str(data["material"]))
        return value

    def material_map(self, mat):
        ''' Converts an input material string to consistent format

        Parameters
        ----------
        mat : str of material name

        Current materials:
        - SS316 (assumed if mat contains "316L" or "316H")
        - IN718 (assumed if mat contains "718")
        '''

        matOut = ""
        mat = mat.upper()
        # For the moment, not differentiating between SS316L and SS316H
        if ("316" in mat) and ("SS" in mat):
            matOut = "SS316"
        elif ("316L" in mat) and ("SS" in mat):
            matOut = "SS316"
        elif ("316H" in mat) and ("SS" in mat):
            matOut = "SS316"
        elif ("718" in mat) and ("IN" in mat):
            matOut = "IN718"
        else:
            print(f'Material "{mat}" is not in template database')
        return matOut

        
    