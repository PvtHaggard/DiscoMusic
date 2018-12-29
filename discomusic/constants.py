import os

CONFIG_PATH = os.path.realpath(path="./config/config.ini")
SERVER_CONFIG_PATH = os.path.realpath(path="./config/server_config.ini")

CONFIG_TEMPLATE = {"discord": {"token": "https://discordapp.com/developers/applications",
                               "admin": "[human readable name]discord_user_id"},
                   "youtube": {"token": "https://console.cloud.google.com/apis/api/youtube.googleapis.com"}}

SERVER_CONFIG_TEMPLATE = {"DEFAULT": {"prefix": '/',
                                      "volume": "1",
                                      "user_blacklist": ""}}
COMMAND_ALIASES = {"p": "pause",
                   "s": "stop",
                   "n": "next",
                   "np": "nowplaying",
                   "h": "help",
                   "v": "volume"}
