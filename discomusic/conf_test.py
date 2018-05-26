from collections import OrderedDict
import configparser
import random
import os
import re


lst = []

for i in lst:
    print(i)

channel = re.search(r"\d{18}(?!channel )", ".no_afk channel 241523419521311516", re.IGNORECASE)
if channel is not None:
    print(channel.group(0))
pass
# config = configparser.ConfigParser(delimiters="=")
#
# path = os.path.realpath(path="../config/server_config.ini")
# print(path)
# if not os.path.isfile(path):
#     raise Exception
# config.read(os.path.realpath(path))
#
# server_id = "TBD"
# if not config.has_section(server_id):
#     config.add_section(server_id)
#     config[server_id] = OrderedDict([('volume', ""),
#                                      ('prefix', ""),
#                                      ('no move channels', ""),
#                                      ('no move time', "")])
#
# with open(path, 'w') as file:
#     config.write(file, space_around_delimiters=False)
