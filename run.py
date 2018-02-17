import sys
import os
import gc
import traceback

venv_path = r"/venv/bin/activate_this.py"

if sys.platform == "win32":
    venv_path = r"/venv/Scripts/activate_this.py"

activate_this = os.path.normpath(os.getcwd() + venv_path)


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
