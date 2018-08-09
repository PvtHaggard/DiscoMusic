from discomusic import constants


class ConfigFileMissing(Exception):
    def __init__(self):
        super().__init__("No config file found in '{}'".format(constants.CONFIG_PATH))


class ConfigValueError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


