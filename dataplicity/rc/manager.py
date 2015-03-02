import weakref

from .keyboard import Keyboard
from .button import ButtonGroup

import logging
log = logging.getLogger('m2m.rc')


class NoKeyboardError(KeyError):
    pass


class RCManager(object):
    """Manage remote controls (keyboards, buttons etc) over m2m"""

    def __init__(self, m2m):
        self._m2m = weakref.ref(m2m)
        self.keyboards = {}
        self.button_groups = {}
        self.bindings = {}

    @property
    def m2m(self):
        return self._m2m()

    @property
    def client(self):
        return self.m2m.client

    def __repr__(self):
        return "<rcmanager>"

    @classmethod
    def init_from_conf(cls, client, conf):
        manager = cls(client.m2m)
        log.debug('starting RC manager')

        for section, name in conf.qualified_sections('keyboard'):
            keyboard = manager.add_keyboard(name)
            log.debug("%r created", keyboard)

        for section, name in conf.qualified_section('button'):
            group = conf.get('section', 'group')
            button_group = manager.add_button_group(group)
            button_group.add_button(name, conf, section)

        return manager

    def open_keyboard(self, name, channel):
        log.debug('opening keyboard')
        keyboard = self.get_keyboard(name)
        log.debug('%r', keyboard)
        keyboard.make_instance(channel)

    def add_keyboard(self, name):
        """Add a named keyboard"""
        keyboard = self.keyboards[name] = Keyboard(self.client, name)
        return keyboard

    def get_keyboard(self, name):
        """Get a named keyboard"""
        try:
            return self.keyboards[name]
        except KeyError:
            raise NoKeyboardError("no keyboard called '{}'".format(name))

    def add_button_group(self, name):
        if name not in self.button_groups:
            self.button_groups[name] = ButtonGroup(self.client, name)
        return self.button_groups[name]