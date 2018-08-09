import os

CONFIG_PATH = os.path.realpath(path="./config/config.ini")
SERVER_CONFIG_PATH = os.path.realpath(path="./config/server_config.ini")

CONFIG_TEMPLATE = {"bot": {"discord_token": "https://discordapp.com/developers/applications",
                           "admin": "[name]discord_user_id"},
                   "google API": {"key": "https://console.cloud.google.com/apis/api/youtube.googleapis.com"}}

SERVER_CONFIG_TEMPLATE = {"DEFAULT": {"prefix": '/',
                                      "volume": "0.5",
                                      "blacklist": ""}}
