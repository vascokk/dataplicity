from __future__ import unicode_literals
from .device import Device

import threading
from collections import defaultdict

import logging
log = logging.getLogger('m2m.rc')


class Key(object):
    """The state of an individual key"""
    def __init__(self, code):
        self.code = code
        self.pressed = False

    def __repr__(self):
        return "<key {} '{}'>".format(self.code, unichr(self.code))

    def on_down(self):
        self.pressed = True
        log.debug('%r DOWN')

    def on_up(self):
        self.pressed = False
        log.debug('%r UP')


class KeyboardInstance(object):

    def __init__(self, channel):
        log.debug('keyboard over %r', channel)
        channel.set_callbacks(on_data=self.on_data)

    def on_data(self, data):
        log.debug(repr(data))


class Keyboard(Device):
    """The state of a remote keyboard"""

    def __init__(self, name):
        super(Keyboard, self).__init__(name)
        self._keys = defaultdict(Key)

    def __repr__(self):
        return "<rckeyboard '{}'>".format(self.name)

    def make_instance(self, channel):
        return KeyboardInstance(channel)

    def on_event(self, event):
        get = event.get
        if get('device', None) != 'keyboard':
            return
        with self.lock:
            event_type = get('type', None)
            key = self._get_key(event['which'])
            if event_type == 'keydown':
                key.on_down()
            elif event_type == 'keyup':
                key.on_up()
            else:
                log.error('unknown keyboard event %r', event_type)

    def reset(self):
        """Reset the keyboard to an unpressed state"""
        self._keys.clear()

    def _get_key(self, code):
        if isinstance(code, basestring):
            code = ord(code[0])
        return self.keys[code]

    def is_pressed(self, key):
        """Check if a given key is pressed"""
        return self._get_key(key).pressed

    def get_pressed(self):
        """Get a set of keys that are currently pressed"""
        with self.lock:
            return set([key for key in self._keys.values() if key.pressed])
