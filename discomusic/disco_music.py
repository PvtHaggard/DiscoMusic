from urllib.parse import urlparse, parse_qs
from configparser import ConfigParser
import logging
import asyncio
import json
import time
import os
import re

import discord
import requests

from discomusic import exceptions, constants

log = logging.getLogger("discomusic")

# TODO: cmd_join
# TODO: cmd_leave

# TODO: cmd_play cmd_p
# TODO: cmd_stop cmd_s
# TODO: cmd_pause
# TODO: cmd_restart
# TODO: cmd_repeat
# TODO: cmd_next
# TODO: cmd_replay
# TODO: cmd_clear
# TODO: cmd_nowplaying cmd_np
# TODO: cmd_list

# TODO: cmd_cleanup
# TODO: cmd_help cmd_h
# TODO: cmd_develop
# TODO: cmd_admin restart


def bot_admin(func):
    async def authenticate(self, *args, **kwargs):
        admins = []
        for i in self.config["discord"]["admins"].split():
            admins += i.split(']')

        if args[0].author.id not in admins:
            await self.send_message(args[0].channel, "This command requires administrator privileges.")
            return
        return await func(self, *args, **kwargs)
    return authenticate


def server_admin(func):
    async def authenticate(self, *args, **kwargs):
        if args[0].author.server_permissions.administrator:
            return await func(self, *args, **kwargs)
        await self.send_message(args[0].channel, "This command requires server administrator privileges.")
        return

    return authenticate


def blacklist(func):
    async def authenticate(self, *args, **kwargs):
        if self.sever_configs.has_section(args[0].server.id):
            bl = self.sever_configs.get(args[0].server.id, "blacklist").split()
        else:
            bl = []

        if args[0].author.id not in bl:
            return await func(self, *args, **kwargs)
        await self.send_message(args[0].channel, "You can not do that.")
        return

    return authenticate


def disable(func):
    return


class DiscoMusic(discord.Client):
    def __init__(self):
        self.config = self.load_config()
        self.sever_configs = self.load_server_configs()

        self.voice_states = {}
        print(constants.CONFIG_PATH)
        super().__init__()

    def run(self):
        try:
            self.loop.run_until_complete(self.start(self.config.get("bot", "discord_token")))
        except SystemExit:
            self.loop.run_until_complete(self.logout())
            pending = asyncio.Task.all_tasks(loop=self.loop)
            gathered = asyncio.gather(*pending, loop=self.loop)
            try:
                gathered.cancel()
                self.loop.run_until_complete(gathered)

                # we want to retrieve any exceptions to make sure that
                # they don't nag us about it being un-retrieved.
                gathered.exception()
            except:
                pass
        finally:
            self.loop.close()

    async def on_ready(self):
        log.info("Bot ready")
        await self.change_presence(game=discord.Game(name="In Development"))

    async def on_message(self, message: discord.Message):
        if self.sever_configs.has_section(message.server.id):
            prefix = self.sever_configs.get(message.server.id, "prefix")
        else:
            prefix = self.sever_configs.get("DEFAULT", "prefix")

        if message.content.startswith(prefix):
            try:
                command = message.content.split()[0][1:]
                if command in constants.COMMAND_ALIASES.keys():
                    command = constants.COMMAND_ALIASES[command]

                func = getattr(self, "cmd_" + command)

            except AttributeError as e:
                log.debug(e)
                await self.send_message(message.channel, "That is not a valid command")
                return
            except TypeError:
                log.debug("cmd_{} is disabled".format(message.content.split()[0][1:]))
                await self.send_message(message.channel, "That command is disabled")
                return

            try:
                await func(message)
            except discord.errors.Forbidden:
                await self.send_message(message.channel, "Forbidden, missing permissions")

    @server_admin
    async def cmd_purge(self, message: discord.Message):
        offset = 2  # Used to account for the users message and the bots reply.
        limit = 5  # Number of messages to remove

        # Tries to convert the argument into an int
        # If it fails the default limit of 5 is used
        try:
            limit = int(message.content.split(' ')[-1])
        except ValueError:
            # Will user DEFAULT limit value
            await self.send_message(message.channel, "Invalid limit, defaulting to 5 posts.".format(limit))
            offset += 1
            pass

        reply = await self.send_message(message.channel, "Purge {} posts from channel, are you sure?".format(limit))

        await self.add_reaction(reply, '✔')
        await self.add_reaction(reply, '✖')

        reaction = await self.wait_for_reaction(['✔', '✖'], message=reply, timeout=10, user=message.author)

        if reaction.reaction.emoji == '✔':
            await self.purge_from(message.channel, limit=limit + offset)
        else:
            await self.delete_message(message)
            await self.delete_message(reply)

    @bot_admin
    @server_admin
    async def cmd_cleanup(self, message: discord.Message):
        if self.sever_configs.has_section(message.server.id):
            server_id = message.server.id
        else:
            server_id = "DEFAULT"

        messages = []
        async for msg in self.logs_from(message.channel, limit=100):
            if msg.author == self.user:
                messages.append(msg)
            elif msg.content.startswith(self.sever_configs.get(server_id, "prefix")):
                messages.append(msg)

        await self.delete_messages(messages)

    @server_admin
    async def cmd_volume(self, message: discord.Message):
        volume = int(message.content.split()[1])

        if volume > 100 or volume < 1:
            self.send_message(message.channel, "Volume must be between 0 and 100")
            return

        server = "DEFAULT"

        if self.sever_configs.has_section(message.server.id):
            server = str(message.server.id)

        self.update_server_config(message.server.id, volume=float(volume) / 100)

        await self.send_message(message.channel, "Volume set to {:d} was {:.0f}".format(volume, self.sever_configs.getfloat(server, "volume") * 100))

    @server_admin
    async def cmd_prefix(self, message: discord.Message):
        prefix = message.content.split()[1]
        if len(prefix) != 1:
            self.send_message(message.channel, "Prefix must be a single character")
            return

        server = "DEFAULT"
        if self.sever_configs.has_section(message.server.id):
            server = str(message.server.id)

        await self.send_message(message.channel, "Prefix set to {:s} was {:s}".format(prefix, self.sever_configs.get(server, "prefix")))

        self.update_server_config(message.server.id, prefix=prefix)

    # TODO: Finish/fix
    @bot_admin
    async def cmd_shutdown(self, message: discord.Message):
        await self.send_message(message.channel, "Shutting down bot!")
        await self.logout()

    def get_playlist(self, list_id):
        def build_playlist(json_data):
            prefix = "www.youtube.com/watch?v="
            urls = {}
            for i in json_data["items"]:
                urls[i["snippet"]["title"]] = prefix + i["snippet"]["resourceId"]["videoId"]
            return urls

        api_url = "https://www.googleapis.com/youtube/v3/playlistItems?key={}&playlistId={}&part=snippet&maxResults=50"
        log.debug(api_url.format(self.config.get("google API", "key"), list_id[0]))
        page = requests.get(api_url.format(self.config.get("google API", "key"), list_id[0]))
        page.raise_for_status()
        return build_playlist(json.loads(page.text))

    @staticmethod
    def load_config():
        config_parser = ConfigParser()

        if not os.path.isfile(constants.CONFIG_PATH):
            # TODO: should create folder structure as well?
            log.error("Config file missing, template generated in: {}".format(constants.CONFIG_PATH))

            if not os.path.exists(os.path.dirname(constants.CONFIG_PATH)):
                os.makedirs(os.path.dirname(constants.CONFIG_PATH))

            with open(constants.CONFIG_PATH, "w+") as file:
                config_parser.read_dict(constants.CONFIG_TEMPLATE)
                config_parser.write(file)

            raise exceptions.ConfigFileMissing()

        config_parser.read(constants.CONFIG_PATH)
        return config_parser

    @staticmethod
    def load_server_configs():
        config_parser = ConfigParser()

        if not os.path.isfile(constants.SERVER_CONFIG_PATH):
            log.info("Server config missing, default config generated in: {}".format(constants.SERVER_CONFIG_PATH))
            with open(constants.SERVER_CONFIG_PATH, "w+") as file:
                config_parser.read_dict(constants.SERVER_CONFIG_TEMPLATE)
                config_parser.write(file)

        config_parser.read(constants.SERVER_CONFIG_PATH)
        return config_parser

    def update_server_config(self, server_id, **kwargs):
        if not self.sever_configs.has_section(server_id):
            self.sever_configs.add_section(server_id)

        for key in kwargs:
            self.sever_configs[str(server_id)][key] = str(kwargs[key])

        with open(constants.SERVER_CONFIG_PATH, 'w') as file:
            self.sever_configs.write(file)


    # async def cmd_no_afk(self, message: discord.Message):
    #     # .no_afk channel 241523419521351680
    #     # .no_afk @USER     (Default time sever set)
    #     # .no_afk @USER 1h30m
    #     # .no_afk @USER1 @USER2 @USER3 1h30m
    #     # .no_afk 1h30ms
    #
    #     channel = re.search(r"\d{18}(?!channel )", message.content, re.IGNORECASE)
    #     if channel is not None:
    #         # TODO: Add channel to servers no move
    #         return
    #
    #     minutes = 0
    #     try:
    #         minutes += int(re.search(r"\d+(?=h)", message.content, re.IGNORECASE).group(0)) * 60
    #     except AttributeError:
    #         pass
    #     try:
    #         minutes += int(re.search(r"\d+(?=m)", message.content, re.IGNORECASE).group(0))
    #     except AttributeError:
    #         pass
    #
    #     if minutes == 0:
    #         if message.author.id in self.no_afk_members.keys():
    #             del self.no_afk_members[message.author.id]
    #             await self.send_message(message.channel, "AFK lock removed")
    #             return
    #
    #         minutes = 30
    #     for mention in message.mentions:
    #         self.no_afk_members[mention] = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    #     else:
    #         self.no_afk_members[message.author.id] = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    #
    #     await self.send_message(message.channel, "Preventing voice chat timeout for {} minutes".format(minutes))
