'''A general Component subclass with no input or output file requirements'''
from .component import *

class ComponentGeneral(Component):
    def __init__(self):
        Component.__init__(self)

    def get_input_files(self):
        return []
        
    def get_output_files(self):
        return []

    def check_output_files(self, files):
        return []

