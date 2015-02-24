import weakref

from .keyboard import Keyboard

import logging
log = logging.getLogger('m2m.rc')


class NoKeyboardError(KeyError):
    pass


class RCManager(object):
    """Manage remote controls (keyboards, buttons etc) over m2m"""

    def __init__(self, m2m):
        self._m2m = weakref.ref(m2m)
        self.keyboards = {}
        self.bindings = {}

    @property
    def m2m(self):
        return self._m2m()

    def __repr__(self):
        return "<rcmanager>"

    @classmethod
    def init_from_conf(cls, client, conf):
        manager = cls(client.m2m)
        log.debug('starting RC manager')
        for section, name in conf.qualified_sections('keyboard'):
            keyboard = manager.add_keyboard(name)
            log.debug("%r created", keyboard)
        return manager

    def open_keyboard(self, name, channel):
        log.debug('opening keyboard')
        keyboard = self.get_keyboard(name)
        log.debug('%r', keyboard)
        keyboard.make_instance(channel)

    def add_keyboard(self, name):
        """Add a named keyboard"""
        keyboard = self.keyboards[name] = Keyboard(name)
        return keyboard

    def get_keyboard(self, name):
        """Get a named keyboard"""
        try:
            return self.keyboards[name]
        except KeyError:
            raise NoKeyboardError("no keyboard called '{}'".format(name))
