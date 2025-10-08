"""Module for applications using the adamantine finite element heat transfer and
thermomechanical evolution (https://github.com/adamantine-sim/adamantine)"""

from .adamantine import AdamantineApp
from .input_file import input_file_to_dict, write_dict_to_input_file
from .scanpath import convert_myna_local_scanpath_to_adamantine
