from __future__ import unicode_literals
from __future__ import print_function

"""
Settings synced with the server

"""

from dataplicity.client.settings import read_contents
from dataplicity import atomicwrite
from dataplicity.compat import iteritems

from io import BytesIO
import os
from os.path import join
from threading import RLock
from shutil import copyfile


import logging
log = logging.getLogger('dataplicity')


class LiveSettingsManager(object):
    """Manages settings files that may be modified by the server"""

    def __init__(self, path, device_class):
        self.path = path
        self.device_class = device_class
        self._settings = {}
        self.lock = RLock()
        super(LiveSettingsManager, self).__init__()

    @classmethod
    def init_from_conf(cls, client, conf):
        settings_path = conf.get_path('device', 'settings', None)
        device_class = conf.get('device', 'class')
        if settings_path is None:
            manager = LiveSettingsManager(None, device_class)
        else:
            manager = LiveSettingsManager(settings_path, device_class)
            for section, name in conf.qualified_sections('settings'):
                if not conf.get_bool(section, 'enabled', True):
                    continue
                defaults_path = conf.get_path(section, 'defaults')
                manager.add(name, defaults_path)
            manager._init()
        return manager

    def _init(self):
        for settings in self._settings.values():
            settings.init()

    def add(self, name, defaults_path):
        """Add a named live settings object"""
        filename = "{}.conf".format(name)
        settings_dir = join(self.path, self.device_class)
        if not os.path.exists(settings_dir):
            log.debug("creating settings directory {}".format(settings_dir))
            try:
                os.makedirs(settings_dir)
            except OSError as e:
                log.error("unable to create settings directory ({})".format(e))
        path = join(settings_dir, filename)
        log.debug("adding settings '{}' from path {}".format(name, path))
        self._settings[name] = LiveSettings(path, defaults_path)

    def get(self, name, reload=True):
        """Get a live settings object, may prompt a reload if necessary"""
        with self.lock:
            live_settings = self._settings[name]
            live_settings.check(reload=reload)
            return live_settings.settings

    def _update(self, name, settings_contents):
        """Update a settings file with new contents"""
        settings = self.get(name, reload=False)
        settings.write(settings_contents)

    def jsonify(self):
        """Get the live settings in serialized form"""
        settings_serialized = {name: settings.jsonify()
                               for name, settings in iteritems(self._settings)}
        return settings_serialized

    @property
    def contents_map(self):
        """Gets a dict that maps the conf name on to the file contents"""
        return {name: conf.contents
                for name, conf in iteritems(self._settings)}

    def startup(self, tasks):
        if self._settings:
            for name, conf in iteritems(self._settings):
                settings = self._settings[name]
                tasks.send_signal_from('settings_update', name, name, settings.settings)

    def update(self, conf_map, tasks):
        """Update new conf files"""
        with self.lock:
            for name, conf in iteritems(conf_map):
                settings = self._settings[name]
                settings.write(conf)
                tasks.send_signal_from('settings_update', name, name, settings.settings)


class LiveSettings(object):
    """Settings object that may be updated by the server"""

    def __init__(self, path, defaults_path):
        self.path = path
        self.defaults_path = defaults_path
        self._settings = None
        self.timestamp = None
        self._contents = None

    def __repr__(self):
        return '<settings "{}">'.format(self.path)

    @property
    def contents(self):
        return self.export()

    @property
    def settings(self):
        self.check()
        return self._settings

    def init(self):
        if os.path.exists(self.defaults_path):
            if not os.path.exists(self.path):
                # New settings, just copy value
                copyfile(self.defaults_path, self.path)
                log.debug('copied default settings from {} to {}'.format(self.defaults_path, self.path))
            else:
                # Settings already exists
                # Attempt to merge any new default values
                _contents, default_settings = read_contents(self.defaults_path, blank=True)
                updated = False
                for section in default_settings.sections():
                    for option in default_settings.options(section):
                        if not self.settings.has_option(section, option):
                            value = default_settings.get(section, option)
                            self.settings.set(section, option, value)
                            log.debug('added new default to {} {}/{}="{}"'.format(self, section, option, value))
                            updated = True
                if updated:
                    self.export()
        self.load()

    def get_timestamp(self):
        try:
            return os.path.getmtime(self.path)
        except OSError:
            return 0

    @property
    def changed(self):
        """Check if the settings file has changed since it was last read"""
        return self.timestamp is None or self.timestamp != self.get_timestamp()

    def check(self, reload=False):
        """Load the settings file if required"""
        if self._settings is None:
            self.load()
        elif reload and self.changed:
            self.load()
        return self

    def load(self):
        """"Load the live settings"""
        try:
            timestamp = self.get_timestamp()
            self._contents, self._settings = read_contents(self.path, blank=True)
            self.timestamp = timestamp
        except Exception:
            log.exception('Error reading live settings from "{}"'.format(self.path))
            return False
        return True

    def export(self):
        """Write the settings objects to a string"""
        f = BytesIO()
        self.settings.write(f)
        contents = f.getvalue()
        f.close()
        return contents

    def write(self, contents):
        """Write out the new contents of a settings file"""
        with atomicwrite.open(self.path, 'wt') as f:
            f.write(contents)
        self._settings = None
        self.load()

    def jsonify(self):
        """Settings in a json object"""
        return {
            "timestamp": self.timestamp,
            "settings": self._contents
        }
