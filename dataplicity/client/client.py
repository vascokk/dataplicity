from dataplicity.client import settings, serial
from dataplicity.client.task import TaskManager
from dataplicity.client.sampler import SamplerManager
from dataplicity.client.livesettings import LiveSettingsManager
from dataplicity.client.timeline import TimelineManager
from dataplicity.app import comms
from dataplicity.jsonrpc import JSONRPC
from dataplicity import errors
from dataplicity.constants import *
from dataplicity import firmware


from time import time
import os.path
import logging
import random


class Client(object):
    """The main interface to the dataplicity server"""

    def __init__(self, conf_paths, check_firmware=True, log=None):
        self.check_firmware = check_firmware
        if log is None:
            log = logging.getLogger('dataplicity.client')
        self.log = log
        conf_paths = conf_paths or None
        if not isinstance(conf_paths, list):
            conf_paths = [conf_paths]
        conf = self.conf = settings.read(*conf_paths)
        conf_dir = os.path.dirname(conf.path)
        self._init(conf, conf_dir)

    def _init(self, conf, conf_dir):
        self.firmware_conf = settings.read_default(os.path.join(conf_dir, 'firmware.conf'))
        self.current_firmware_version = int(self.firmware_conf.get('firmware', 'version', 1))
        self.log.info('running firmware {:010}'.format(self.current_firmware_version))
        self.rpc_url = conf.get('server',
                                'url',
                                SERVER_URL)
        self.remote = JSONRPC(self.rpc_url)

        self.serial = conf.get('device', 'serial', None)
        if self.serial is None:
            self.serial = serial.get_default_serial()
            self.log.info('auto generated device serial, %r', self.serial)
        self.device_class = conf.get('device', 'class')
        self.auth_token = conf.get('device', 'auth')

        self.tasks = TaskManager.init_from_conf(self, conf)
        self.samplers = SamplerManager.init_from_conf(self, conf)
        self.livesettings = LiveSettingsManager.init_from_conf(self, conf)
        self.timelines = TimelineManager.init_from_conf(self, conf)

        self.sample_now = self.samplers.sample_now
        self.sample = self.samplers.sample

        self.get_timeline = self.timelines.get_timeline

    def get_settings(self, name):
        self.livesettings.get(name, reload=True)

    def sync(self):
        start = time()
        self.log.debug("syncing...")

        if not self.auth_token:
            self.log.error("sync failed -- no auth token, have you run 'dataplicity register'?")
            return

        samplers_updated = []
        random.seed()
        sync_id = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in xrange(12))
        with self.remote.batch() as batch:

            # Authenticate
            batch.call_with_id('authenticate_result',
                               'device.check_auth',
                               device_class=self.device_class,
                               serial=self.serial,
                               auth_token=self.auth_token,
                               sync_id=sync_id)

            if self.check_firmware:
                batch.call_with_id('firmware_result',
                                   'device.check_firmware',
                                   current_version=self.current_firmware_version)

            # Add samples
            for sampler_name in self.samplers.enumerate_samplers():
                sampler = self.samplers.get_sampler(sampler_name)
                samples = sampler.snapshot_samples()
                if samples:
                    batch.call_with_id("samples.{}".format(sampler_name),
                                       "device.add_samples",
                                       device_class=self.device_class,
                                       serial=self.serial,
                                       sampler_name=sampler_name,
                                       samples=samples)
                    samplers_updated.append(sampler_name)
                else:
                    sampler.remove_snapshot()

            # Update conf
            conf_map = self.livesettings.contents_map
            batch.call_with_id("conf_result",
                               "device.update_conf_map",
                               conf_map=conf_map)

            # Update timeline(s)
            if self.timelines:
                for timeline in self.timelines:
                    batch.call_with_id('timeline_result_{}'.format(timeline.name),
                                       'device.add_events',
                                       name=timeline.name,
                                       events=timeline.get_events())

        batch.get_result('authenticate_result')

        # Remove snapshots that were successfully synced
        # Unsuccessful snapshots remain on disk, so the next sync will re-attempt them.
        for sampler_name in samplers_updated:
            try:
                if not batch.get_result("samples.{}".format(sampler_name)):
                    self.log("failed to get sampler results '{}'".format(sampler_name))
            except Exception as e:
                self.log.exception("Error adding samples to {} ({})".format(sampler_name, e))
            else:
                sampler.remove_snapshot()

        try:
            changed_conf = batch.get_result("conf_result")
        except:
            self.log.exception('error sending settings')
        else:
            if changed_conf:
                self.livesettings.update(changed_conf, self.tasks)
                changed_conf_names = ", ".join(sorted(changed_conf.keys()))
                self.log.debug("settings file(s) changed: {}".format(changed_conf_names))

        for timeline in self.timelines:
            try:
                timeline_result = batch.get_result('timeline_result_{}'.format(timeline.name))
            except:
                self.log.exception('error sending timeline')
            else:
                timeline.clear_events(timeline_result)

        ellapsed = time() - start
        self.log.debug('sync complete {:0.2f}s'.format(ellapsed))

        if self.check_firmware:
            firmware_result = batch.get_result('firmware_result')
            if firmware_result['current']:
                self.log.debug('firmware is current')
            else:
                firmware_b64 = firmware_result['firmware']
                device_class = firmware_result['device_class']
                version = firmware_result['version']
                self.log.debug("new firmware, version v{} for device class '{}'".format(version, device_class))
                self.log.info("installing firmware v{}".format(version))
                install_path = firmware.install_encoded(device_class, version, firmware_b64)

                self.log('firmware installed in "{}"'.format(install_path))
                comms.Comms().restart()


if __name__ == "__main__":
    client = Client('dataplicity.conf')
