from urllib.parse import urlparse, parse_qs
import traceback
import logging
import asyncio
import json

import discord
import requests

from discomusic import config

log = logging.getLogger("discomusic")


def admin(func):
    async def authenticate(self, *args, **kwargs):
        if args[0].author.id not in self.config.moderators:
            await self.send_message(args[0].channel, "This is an admin only command!")
            return
        return await func(self, *args, **kwargs)
    return authenticate


class DiscoMusic(discord.Client):
    def __init__(self):
        self.config = config.Config()
        self.players = {}
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

    async def cmd_join(self, message: discord.Message):
        log.debug("cmd_join")
        author = message.author
        if author.voice_channel is None:
            await self.send_message(message.channel, "You must join a voice channel so I can join you".format(
                self.config.prefix))
            return

        await self.join_voice_channel(author.voice_channel)

    async def cmd_leave(self, message: discord.Message):
        log.debug("cmd_leave")
        author = message.author
        if self.is_voice_connected(author.server):
            log.debug("Leaving")
            await self.voice_client_in(message.server).disconnect()

    async def cmd_play(self, message: discord.Message):
        log.debug("cmd_play")
        author = message.author
        if not self.is_voice_connected(author.server):
            await self.cmd_join(message)

        if self.voice_client_in(author.server).channel != author.voice_channel:
            await self.voice_client_in(author.server).move_to(author.voice_channel)

        player = self.players.get(message.server, None)

        try:
            cmd_url = message.content.split()[1]
        except IndexError:
            if player is not None:
                player.resume()
            return

        if "list" in parse_qs(urlparse(cmd_url).query):
            try:
                playlist = self.get_playlist(parse_qs(urlparse(cmd_url).query)["list"])
            except requests.exceptions.HTTPError:
                trace = traceback.format_exc()
                log.debug("Something has gone wrong:{}".format(trace))
                await self.send_message(message.channel, "Something has gone wrong. Try another playlist.")
                return
        else:
            playlist = [cmd_url]

        log.debug("{} song/s added to playlist.".format(len(playlist)))
        await self.send_message(message.channel, "`{}` videos added to playlist.".format(len(playlist)))

        if player is None:
            voice = self.voice_client_in(author.server)
            # player = voice.create_ffmpeg_player(os.path.realpath(path="./cache/Amber Run - I Found.wma"))
            player.volume = self.config.volume
            player.start()
            self.players[message.server] = player

    async def cmd_stop(self, message: discord.Message):
        log.debug("cmd_stop")
        player = self.players.get(message.server, None)
        if player is None:
            await self.send_message(message.channel, "I'm not playing anything.")
        else:
            player.stop()

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

    @admin
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

    @admin
    async def cmd_shutdown(self, message: discord.Message):
        await self.send_message(message.channel, "Shutting down bot!")
        await self.logout()

    async def cmd_help(self, message: discord.Message):
        await self.send_message(message.author, "TODO")

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


