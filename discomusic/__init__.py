import logging

from .disco_music import DiscoMusic

# Logging setup
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.WARNING)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(asctime)s:%(message)s',
                                              datefmt='%d/%m/%y %I:%M:%S%p'))

discord_logger.addHandler(stream_handler)
log.addHandler(stream_handler)
