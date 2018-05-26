import configparser
import os
import re

import discomusic.exceptions


class BotConfig:
    def __init__(self):
        super().__init__()
        self.load_config()

        # Discord login
        self.discord_token = self.get("bot", "discord_token", fallback=None)

        # Google YouTube API
        self.google_key = self.get("google API", "key", fallback=None)

        self.prefix = self.get("config", "prefix", fallback='/')
        self.volume = self.getfloat("config", "volume", fallback=0.5)

        # Bot Admins/Dev
        self.admins = re.findall(r"(\d{18})", self.get("config", "admins", fallback=""))

        # TODO: This should be moved to a server specific config
        self.channel_whitelist = re.findall(r"(\d{18})", self.get("config", "channel_whitelist", fallback=""))

    def load_config(self):
        path = os.path.realpath(path="./config/config.ini")
        if not os.path.isfile(path):
            raise discomusic.exceptions.ConfigFileMissing()

        self.read(os.path.realpath(path))


# bot = discord_token, google_key, cmd_prefix, volume, bot_admin, afk_timeout_mins
# server = server_id, cmd_prefix, volume, channel_whitelist, afk_timeout_mins, afk_timeout_channels