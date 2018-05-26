from urllib.parse import urlparse, parse_qs
import traceback
import datetime
import logging
import asyncio
import json
import time
import re

import discord
import requests

from discomusic import config, music_player

log = logging.getLogger("discomusic")

# TODO: cmd_join
# TODO: cmd_leave

# TODO: cmd_play
# TODO: cmd_stop
# TODO: cmd_pause
# TODO: cmd_skip

# TODO: cmd_nowplaying
# TODO: cmd_list

# TODO: cmd_volume
# TODO: cmd_showconfig

# TODO: cmd_help
# TODO: cmd_restart


def bot_admin(func):
    async def authenticate(self, *args, **kwargs):
        if args[0].author.id not in self.config.admins:
            await self.send_message(args[0].channel, "This command requires bot host privileges.")
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


def disable(func):
    return


class DiscoMusic(discord.Client):
    def __init__(self):
        self.config = config.BotConfig()
        self.voice_states = {}
        self.no_afk_members = {}  # {user ID: unlock time]
        super().__init__()

    def run(self):
        try:
            self.loop.run_until_complete(self.start(self.config.discord_token))
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
        log.debug("Bot ready")
        await self.change_presence(game=discord.Game(name="In Development"))

    async def on_message(self, message: discord.Message):
        if len(self.config.channel_whitelist) > 0:
            if message.channel.id not in self.config.channel_whitelist:
                return

        if message.content[0] == self.config.prefix:
            try:
                await getattr(self, "cmd_" + message.content.split()[0][1:])(message)
            except AttributeError as e:
                log.debug(e)
                await self.send_message(message.channel, "That is not a valid command")
            except TypeError:
                log.debug("cmd_{} is disabled".format(message.content.split()[0][1:]))
                await self.send_message(message.channel, "That command is disabled")

    @server_admin
    async def cmd_purge(self, message: discord.Message):
        offset = 2  # Used to account for the users message and the bots reply.
        limit = 5  # Number of messages to remove

        # Tries to convert the argument into an int
        # If it fails the default limit of 100 is used
        try:
            limit = int(message.content.split(' ')[-1])
        except ValueError:
            # Will user default limit value
            pass

        log.info("User: {} tried to purge {} messages from channel {}/{}".format(message.author.name, limit, message.server.name, message.channel.name))
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
        log.debug(api_url.format(self.config.google_key, list_id[0]))
        page = requests.get(api_url.format(self.config.google_key, list_id[0]))
        page.raise_for_status()
        return build_playlist(json.loads(page.text))

    async def cmd_no_afk(self, message: discord.Message):
        # .no_afk channel 241523419521351680
        # .no_afk @USER     (Default time sever set)
        # .no_afk @USER 1h30m
        # .no_afk @USER1 @USER2 @USER3 1h30m
        # .no_afk 1h30ms

        channel = re.search(r"\d{18}(?!channel )", message.content, re.IGNORECASE)
        if channel is not None:
            # TODO: Add channel to servers no move
            return

        minutes = 0
        try:
            minutes += int(re.search(r"\d+(?=h)", message.content, re.IGNORECASE).group(0)) * 60
        except AttributeError:
            pass
        try:
            minutes += int(re.search(r"\d+(?=m)", message.content, re.IGNORECASE).group(0))
        except AttributeError:
            pass

        if minutes == 0:
            if message.author.id in self.no_afk_members.keys():
                del self.no_afk_members[message.author.id]
                await self.send_message(message.channel, "AFK lock removed")
                return

            minutes = 30
        for mention in message.mentions:
            self.no_afk_members[mention] = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        else:
            self.no_afk_members[message.author.id] = datetime.datetime.now() + datetime.timedelta(minutes=minutes)

        await self.send_message(message.channel, "Preventing voice chat timeout for {} minutes".format(minutes))
