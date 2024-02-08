import argparse


def is_bool_action(option_type):
    if (option_type == argparse._StoreFalseAction) or (
        option_type == argparse._StoreTrueAction
    ):
        return True
    else:
        return False


def get_script_call_with_defaults(parser, args):
    """Get the full command_args from the script input,
    including unspecified default values

    Parameters:
    - parser = argparse.ArgumentParser() object
    - args = input command_args line arguments from parser.parse_args()
    """

    # Get all defaults
    all_defaults = {}
    for key in vars(args):
        all_defaults[key] = parser.get_default(key)

    # Get option strings
    option_strings = [
        x.option_strings[0]
        for x in parser.__dict__["_actions"]
        if type(x) is not argparse._HelpAction
    ]
    option_types = [
        type(x)
        for x in parser.__dict__["_actions"]
        if type(x) is not argparse._HelpAction
    ]

    # Parse args into the command_args line equivalent
    command_args = []
    for option, option_type, key, arg in zip(
        option_strings, option_types, all_defaults, vars(args)
    ):
        cmd_string = None
        default_value = all_defaults[key]
        arg_value = args.__getattribute__(arg)
        print(
            f"{option} : {key} = {arg_value} : <default> {key} = {default_value} ({option_type})"
        )
        if arg_value == default_value:
            if is_bool_action(option_type):
                pass
            else:
                cmd_string = f"{option} {default_value}"
        else:
            if is_bool_action(option_type):
                cmd_string = f"{option}"
            else:
                cmd_string = f"{option} {arg_value}"
        if cmd_string is not None:
            command_args.append(cmd_string)

    return command_args
