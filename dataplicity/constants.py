from __future__ import unicode_literals
from __future__ import print_function

import os

SERVER_URL = os.environ.get('DATAPLICITY_API_URL', "https://api.dataplicity.com")
PUSH_URL = "https://sync.dataplicity.com/pushwait/"
CONF_PATH = "/etc/dataplicity/dataplicity.conf"
SETTINGS_PATH = "/var/dataplicity/"
FIRMWARE_PATH = "/srv/dataplicity/fw/"
TIMELINE_PATH = "/tmp/dataplicitytimeline/"
PID_PATH = "/var/run/dataplicity.pid"
M2M_URL = "wss://m2m.dataplicity.com/m2m/"
