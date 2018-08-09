import os


class ConfigFileMissing(Exception):
    def __init__(self):
        super().__init__("No config file found in '{}'".format(os.path.realpath(path="./config/config.ini")))


class ConfigValueError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


