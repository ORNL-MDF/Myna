'''Base class for Myna file'''

class File:
    def __init__(self, file):
        self.file = file

    def file_is_valid(self):
        '''Check if file is valid based on class/subclass requirements'''
        raise NotImplementedError


    