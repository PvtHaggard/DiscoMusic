import configparser
import os
import re

import discomusic.exceptions


class Config(configparser.ConfigParser):
    def __init__(self):
        super().__init__()
        self.load_config()

        # Discord login
        self.discord_token = self.get("bot", "discord_token", fallback=None)

        # Google YouTube API
        self.google_key = self.get("google API", "key", fallback=None)

        self.prefix = self.get("config", "prefix", fallback='/')
        self.volume = self.getfloat("config", "volume", fallback=0.5)

        self.admins = re.findall(r"(\d{18})", self.get("config", "admins", fallback=""))
        self.moderators = re.findall(r"(\d{18})", self.get("config", "moderators", fallback="")) + self.admins

        self.channel_whitelist = re.findall(r"(\d{18})", self.get("config", "channel_whitelist", fallback=""))

    def load_config(self):
        path = os.path.realpath(path="./config/config.ini")
        if not os.path.isfile(path):
            raise discomusic.exceptions.ConfigFileMissing()

        self.read(os.path.realpath(path))
