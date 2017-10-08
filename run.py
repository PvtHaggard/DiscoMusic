import sys
import os
import gc
import aiohttp
import traceback

if sys.platform == "win32":
    activate_this = os.path.normpath(os.getcwd() + r"/venv/Scripts/activate_this.py")
else:
    activate_this = os.path.normpath(os.getcwd() + r"/venv/bin/activate_this.py")


with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

from discomusic import DiscoMusic


try:
    bot = DiscoMusic()
    bot.run()
except RuntimeError as e:
    print("WHY THE FUCK ARE YOU NOT CLOSED!!!!")
    print(traceback.format_exc())
    pass
finally:
    gc.collect()
