"""Conversion functions"""


def str_to_list(str_list):
    """Converts string containing list to Python list"""
    output = None
    if type(str_list) == str:
        output = str_list.replace("[", "").replace("]", "").replace(" ", "").split(",")
    return output
