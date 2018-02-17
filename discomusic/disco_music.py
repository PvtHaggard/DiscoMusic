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


def bot_admin(func):
    async def authenticate(self, *args, **kwargs):
        if args[0].author.id not in self.config.admins:
            await self.send_message(args[0].channel, "This is an admin only command!")
            return
        return await func(self, *args, **kwargs)
    return authenticate


def server_admin(func):
    async def authenticate(self, *args, **kwargs):
        if args[0].author.id not in self.config.admins:
            await self.send_message(args[0].channel, "This is an admin only command!")
            return
        return await func(self, *args, **kwargs)
    return authenticate


def disable(func):
    return


class DiscoMusic(discord.Client):
    def __init__(self):
        self.config = config.Config()
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
            except TypeError as e:
                log.debug(e)
                await self.send_message(message.channel, "That command is disabled")

    @server_admin
    @disable
    async def cmd_join(self, message: discord.Message):
        author = message.author
        if author.voice_channel is None:
            await self.send_message(message.channel, "You must join a voice channel so I can join you")
            return

        try:
            await self.create_voice_client(author.voice_channel)
        except discord.ClientException:
            await self.voice_client_in(author.server).move_to(author.voice_channel)

        return True

    @disable
    async def cmd_leave(self, message: discord.Message):
        author = message.author
        if self.is_voice_connected(author.server):
            log.debug("Leaving")
            await self.voice_client_in(message.server).disconnect()

    @server_admin
    @disable
    async def cmd_play(self, message: discord.Message):
        state = self.get_voice_state(message.server)
        opts = {'format': 'worstaudio', 'default_search': 'auto', 'quiet': True, 'outtmpl': '/cache/%(title)s.%(ext)s'}

        if state.voice is None:
            success = await self.cmd_join(message)
            if not success:
                return

        #
        #   Split url from message or un-pause music
        try:
            cmd_url = message.content.split()[1]
        except IndexError:
            await self.cmd_pause(message)
            return

        #
        #   Build playlist
        if "list" in parse_qs(urlparse(cmd_url).query):
            log.debug("Found playlist {}".format(cmd_url))
            try:
                playlist = self.get_playlist(parse_qs(urlparse(cmd_url).query)["list"])
                await self.send_message(message.channel, "Found {} song/s in playlist".format(len(playlist)))
            except requests.exceptions.HTTPError:
                trace = traceback.format_exc()
                log.debug("Something has gone wrong:{}".format(trace))
                await self.send_message(message.channel, "Something has gone wrong. Try another playlist.")
                return
        else:
            playlist = [cmd_url]

        print(playlist)

        #
        #   Add each song in the playlist to the player
        for song in playlist:
            try:
                player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
            except Exception:
                log.debug(traceback.format_exc())
            else:
                player.volume = self.config.volume
                entry = music_player.VoiceEntry(message, player)
                await state.songs.put(entry)

    @disable
    async def cmd_stop(self, message: discord.Message):
        log.debug("cmd_stop")
        player = self.players.get(message.server, None)
        if player is None:
            await self.send_message(message.channel, "I'm not playing anything.")
        else:
            player.stop()

    @disable
    async def cmd_pause(self, message: discord.Message):
        log.debug("cmd_pause")
        player = self.players.get(message.server, None)
        if player is None:
            await self.send_message(message.channel, "I'm not playing anything.")
        else:
            player.pause()

    # TODO: cmd_skip
    # TODO: cmd_nowplaying
    # TODO: cmd_list
    # TODO: cmd_volume
    # TODO: cmd_reload_config

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

        log.warning("User: {} tried to purge {} messages from channel {}/{}".format(message.author.name, limit, message.server.name, message.channel.name))
        reply = await self.send_message(message.channel, "Purge {} posts from channel, are you sure?".format(limit))
        await self.add_reaction(reply, '✔')
        await self.add_reaction(reply, '✖')
        reaction = await self.wait_for_reaction(['✔', '✖'], message=reply, timeout=10, user=message.author)

        if reaction.reaction.emoji == '✔':
            await self.purge_from(message.channel, limit=limit + offset)
        else:
            await self.delete_message(message)
            await self.delete_message(reply)

    # TODO: cmd_restart

    @bot_admin
    async def cmd_shutdown(self, message: discord.Message):
        await self.send_message(message.channel, "Shutting down bot!")
        await self.logout()

    @disable
    async def cmd_help(self, message: discord.Message):
        await self.send_message(message.author, "TODO")

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = music_player.VoiceState(self)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.loop.create_task(state.voice.disconnect())
            except:
                pass

    def get_playlist(self, list_id):
        api_url = "https://www.googleapis.com/youtube/v3/playlistItems?key={}&playlistId={}&part=snippet&maxResults=50"
        log.debug(api_url.format(self.config.google_key, list_id[0]))
        page = requests.get(api_url.format(self.config.google_key, list_id[0]))
        page.raise_for_status()
        return self.build_playlist(json.loads(page.text))

    @staticmethod
    def build_playlist(json_data):
        prefix = "www.youtube.com/watch?v="
        urls = {}
        for i in json_data["items"]:
            urls[i["snippet"]["title"]] = prefix + i["snippet"]["resourceId"]["videoId"]
        return urls

    async def cmd_no_afk(self, message: discord.Message):
        # .no_afk channel 241523419521351680
        # .no_afk @USER     (Default time sever set)
        # .no_afk @USER 1h30m
        # .no_afk @USER1 @USER2 @USER3 1h30m
        # .no_afk 1h30m

        channel = re.search(r"\d{18}(?!channel )", message.content, re.IGNORECASE)
        if channel is not None:
            # TODO: Add channel to servers no move
            return

        minutes = 0
        try:
            minutes += int(re.search(r"\d+(?=h)", message.content, re.IGNORECASE).group(0))
        except AttributeError:
            pass

        try:
            minutes += int(re.search(r"\d+(?=m)", message.content, re.IGNORECASE).group(0))
        except AttributeError:
            pass

        self.no_afk_members[message.author.id] = datetime.datetime.now() + datetime.timedelta(minutes=minutes)

        await self.send_message(message.channel, "Preventing voice chat timeout for {} minutes".format(minutes))

    async def on_voice_state_update(self, before: discord.Member, after: discord.Member):
        if after.id not in self.no_afk_members.keys():
            return

        if after.is_afk:
            if (self.no_afk_members[after.id] - datetime.datetime.now()).days == -1:
                del self.no_afk_members[after.id]
            else:
                await self.move_member(after, before.voice_channel)

