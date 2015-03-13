from __future__ import unicode_literals
from __future__ import print_function

from .device import Device

import weakref
import json

import logging
log = logging.getLogger('m2m.rc')


class Key(object):
    """The state of an individual key"""
    def __init__(self, code):
        self.code = code
        self.pressed = False

    def __repr__(self):
        return "<key {}>".format(self.code)

    def on_down(self):
        self.pressed = True

    def on_up(self):
        self.pressed = False


class KeyboardInstance(object):

    def __init__(self, keyboard, channel):
        self._keyboard = weakref.ref(keyboard)
        log.debug('keyboard over %r', channel)
        channel.set_callbacks(on_data=self.on_data)

    @property
    def keyboard(self):
        return self._keyboard()

    def on_data(self, data):
        try:
            key_event = json.loads(data)
        except:
            log.exception('error decoding key event')
            raise
        self.keyboard.on_event(key_event)


class Keyboard(Device):
    """The state of a remote keyboard"""

    def __init__(self, client, name):
        self._client = weakref.ref(client)
        self.name = name
        self._keys = {}
        super(Keyboard, self).__init__(name)

    def __repr__(self):
        return "<rckeyboard '{}'>".format(self.name)

    @property
    def client(self):
        return self._client()

    def make_instance(self, channel):
        return KeyboardInstance(self, channel)

    def on_event(self, event):
        get = event.get
        if get('device', None) != 'keyboard':
            return
        with self.lock:
            event_type = get('type', None)
            key = self._get_key(event['which'])
            if event_type == 'keydown':
                key.on_down()
                self.client.tasks.send_signal_from("keyboard.key_down",
                                                   self.name,
                                                   keyboard=self,
                                                   key=key)
            elif event_type == 'keyup':
                key.on_up()
                self.client.tasks.send_signal_from("keyboard.key_up",
                                                   self.name,
                                                   keyboard=self,
                                                   key=key)
            else:
                log.error('unknown keyboard event %r', event_type)

    def reset(self):
        """Reset the keyboard to an unpressed state"""
        self._keys.clear()

    def _get_key(self, code):
        if code not in self._keys:
            self._keys[code] = Key(code)
        return self._keys[code]

    def is_pressed(self, key):
        """Check if a given key is pressed"""
        return self._get_key(key).pressed

    def get_pressed(self):
        """Get a set of keys that are currently pressed"""
        with self.lock:
            return set([key for key in self._keys.values() if key.pressed])
