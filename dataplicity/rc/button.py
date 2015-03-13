from __future__ import unicode_literals
from __future__ import print_function

import weakref
import json

import logging
log = logging.getLogger('m2m.rc')


class ButtonsInstance(object):
    def __init__(self, button_group, channel):
        self._buttons = weakref.ref(button_group)
        channel.set_callbacks(on_data=self.on_data)
        self.states = {name: False for name in button_group.buttons.keys()}

    def __repr__(self):
        return "<buttons '{}'>".format(self.buttons.name)

    @property
    def buttons(self):
        return self._buttons()

    @property
    def client(self):
        return self.buttons.client

    def is_pressed(self, button):
        return self.states.get(button, False)

    def on_data(self, data):
        try:
            button_event = json.loads(data)
        except:
            log.exception('error decoding button event')
            raise

        button = button_event['name']
        if button not in self.states:
            log.warning("received button event for unknown button '%s'", button)
            return

        if button_event['type'] == 'down':
            self.states[button] = True
            self.client.tasks.send_signal_from("buttons.button_down",
                                               self.buttons.name,
                                               buttons=self,
                                               button=button)

        elif button_event['type'] == 'up':
            self.states[button] = False
            self.client.tasks.send_signal_from("buttons.button_up",
                                               self.buttons.name,
                                               buttons=self,
                                               button=button)


class ButtonGroup(object):
    def __init__(self, client, name):
        self._client = weakref.ref(client)
        self.name = name
        self.buttons = {}

    @property
    def client(self):
        return self._client()

    def __repr__(self):
        return "<buttons '{}'>".format(self.name)

    def add_button(self, name):
        button = Button(name)
        self.buttons[name] = button


    def make_instance(self, channel):
        return ButtonsInstance(self, channel)


class Button(object):

    def __init__(self, name):
        self.name = name
