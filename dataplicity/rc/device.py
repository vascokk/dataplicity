from __future__ import unicode_literals
from __future__ import print_function

from threading import RLock


class Device(object):
    """Base class for a remote device"""

    def __init__(self, name):
        self.name = name
        self.lock = RLock()
        super(Device, self).__init__()

    def on_event(self, event):
        pass
