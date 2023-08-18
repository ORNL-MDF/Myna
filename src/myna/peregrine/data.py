'''Base classes for data requirements'''

class PeregrineBuildData():
    '''Data that requries a build path'''
    
    def __init__(self, build):
        self.file = ""
        self.value = None
        self.unit = ""
        self.build = build

    def load_file_data(self):
        '''Load all data from self.file'''
        raise NotImplementedError

    def value_from_file(self):
        '''Get the data value from self.file'''
        raise NotImplementedError

class PeregrinePartData(PeregrineBuildData):
    '''Data that requries both a build and part path'''
    
    def __init__(self, build, part):
        PeregrineBuildData.__init__(self, build)
        self.part = part