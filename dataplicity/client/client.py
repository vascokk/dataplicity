from __future__ import unicode_literals
from __future__ import print_function

from dataplicity.client import settings, serial, tools
from dataplicity.client.task import TaskManager
from dataplicity.client.sampler import SamplerManager
from dataplicity.client.livesettings import LiveSettingsManager
from dataplicity.client.timeline import TimelineManager
from dataplicity.client.m2m import M2MManager
from dataplicity.rc.manager import RCManager
from dataplicity.client.exceptions import ForceRestart
from dataplicity.jsonrpc import JSONRPC
from dataplicity import constants
from dataplicity import firmware


from fs.zipfs import ZipFS
from fs.osfs import OSFS

from dataplicity.compat import urlopen, HTTPError, xrange

from time import time, sleep
import os
import os.path
import logging
import random
from base64 import b64decode
from threading import Lock, Event
from io import BytesIO

# Number of seconds to wait between failed connections
CONNECT_WAIT = 5


def _wait_on_url(url, closing_event, log):
    """Wait for a long running http request, and respond to a closing event"""

    def do_wait(wait_seconds):
        """Wait for n seconds, or until closing event is set"""
        for _ in xrange(wait_seconds):
            if closing_event.is_set():
                return True
            sleep(1)
        return False

    while not closing_event.is_set():
        url_file = None
        try:
            try:
                url_file = urlopen(url)
            except HTTPError as e:
                # Server probably down or some other connectivity issue
                log.warning("failed to connect to {} ({}), retry in {} seconds".format(url, e, CONNECT_WAIT))
                if do_wait(CONNECT_WAIT):
                    break
                continue
            except Exception:
                # Something else
                log.exception("failed to connect to {}, retry in {} seconds".format(url, CONNECT_WAIT))
                if do_wait(CONNECT_WAIT):
                    break
                continue
            try:
                # This blocks
                # Don't know of a simple way to make it non-blocking with https
                response = url_file.read()
            except:
                log.exception("unable to read response from {}".format(url))
                if do_wait(CONNECT_WAIT):
                    break
                continue

            return response
        finally:
            if url_file is not None:
                url_file.close()
    return None


class Client(object):
    """The main interface to the dataplicity server"""

    def __init__(self, conf_paths, check_firmware=True, log=None, create_m2m=True, rpc_url=None):
        self.check_firmware = check_firmware
        if log is None:
            log = logging.getLogger('dataplicity.client')
        self.log = log
        conf_paths = conf_paths or []
        if not isinstance(conf_paths, list):
            conf_paths = [conf_paths]
        self.conf_paths = conf_paths
        self.create_m2m = create_m2m
        self.rpc_url = rpc_url

        self._sync_lock = Lock()
        self.exit_event = Event()
        self._init()

    def _init(self):
        try:
            conf = self.conf = settings.read(*self.conf_paths)
            conf_dir = os.path.dirname(conf.path)

            self.firmware_conf = settings.read_default(os.path.join(conf_dir, 'firmware.conf'))
            self.current_firmware_version = int(self.firmware_conf.get('firmware', 'version', 1))
            self.firmware_path = conf.get('firmware', 'path', None)
            self.log.info('running firmware {:010}'.format(self.current_firmware_version))
            if self.rpc_url is None:
                self.rpc_url = conf.get('server',
                                        'url',
                                        constants.SERVER_URL)
            self.log.debug('api url is %s', self.rpc_url)
            self.push_url = conf.get('server',
                                     'push_url',
                                     constants.PUSH_URL)
            self.remote = JSONRPC(self.rpc_url)

            self.serial = tools.resolve_value(conf.get('device', 'serial', None))
            if self.serial is None:
                self.serial = serial.get_default_serial()
                self.log.info('auto generated device serial, %r', self.serial)
            self.name = conf.get('device', 'name', self.serial)
            self.log.info('device name "%s", "serial" %s', self.name, self.serial)
            self.device_class = conf.get('device', 'class')
            self.subdomain = conf.get('device', 'subdomain', None)
            if not self.subdomain:
                # try legacy settings
                self.subdomain = conf.get('device', 'company', None)

            self._auth_token = conf.get('device', 'auth')
            self.auto_register_info = conf.get('device', 'auto_device_text', None)

            # Run this first, so it can work asynchronously
            if self.create_m2m:
                self.m2m = M2MManager.init_from_conf(self, conf)
            else:
                self.m2m = None

            if self.m2m:
                self.rc = RCManager.init_from_conf(self, conf)
            else:
                self.rc = None

            self.tasks = TaskManager.init_from_conf(self, conf)
            self.samplers = SamplerManager.init_from_conf(self, conf)
            self.livesettings = LiveSettingsManager.init_from_conf(self, conf)
            self.timelines = TimelineManager.init_from_conf(self, conf)

            self.sample_now = self.samplers.sample_now
            self.sample = self.samplers.sample

            self.get_timeline = self.timelines.get_timeline
        except:
            self.log.exception('unable to start')
            raise

    def close(self):
        self.exit_event.set()
        if self.m2m is not None:
            try:
                self.m2m.close()
            except Exception:
                self.log.exception('error closing m2m')

    def connect_wait(self, closing_event, sync_func):
        def do_wait():
            for _ in range(CONNECT_WAIT):
                if closing_event.is_set():
                    return True
                sleep(1)
            return False
        try:
            while not closing_event.is_set():
                if not self.serial or not self._auth_token or not self.push_url:
                    do_wait()
                    continue
                push_url = "{}?serial={}&auth={}".format(self.push_url,
                                                         self.serial,
                                                         self._auth_token)
                response = _wait_on_url(push_url, closing_event, self.log)
                if response is not None:
                    response = response.strip()
                if response == "SYNCNOW":
                    self.log.debug("server requested sync")
                    try:
                        sync_func()
                    except:
                        self.log.exception("push sync callback failed")
                elif response == "TIMEOUT":
                    # Timed out, just connect again
                    continue
                else:
                    self.log.debug('push wait received: "{}"'.format(response))
                    # Some error occurred, or invalid response
                    # Wait for a moment, so as not to hammer the server
                    do_wait()

        finally:
            self.log.debug('connect_wait thread exiting')

    @property
    def auth_token(self):
        """get the auth_token, which may be in dataplicity.cfg, or reference another file"""
        if self._auth_token.startswith('file:'):
            auth_token_path = self._auth_token.split(':', 1)[-1]
            try:
                with open(auth_token_path, 'rt') as f:
                    auth_token = f.read().strip()
            except IOError:
                return None
            else:
                self._auth_token = auth_token
            return auth_token
        else:
            return self._auth_token

    def get_settings(self, name):
        self.livesettings.get(name, reload=True)

    def get_comms(self):
        from dataplicity.app import comms
        return comms.Comms()

    def sync(self):
        # Serialize syncing
        with self._sync_lock:
            self._sync()

    def set_m2m_identity(self, identity):
        if self.auth_token is not None:
            try:
                self.log.debug('notiying server (%s) of m2m identity (%s)',
                               self.remote.url,
                               identity or '<None>')
                with self.remote.batch() as batch:
                    # Authenticate
                    batch.call_with_id('authenticate_result',
                                       'device.check_auth',
                                       device_class=self.device_class,
                                       serial=self.serial,
                                       auth_token=self.auth_token)
                    batch.notify('m2m.associate', identity=identity or '')
                return identity
            except:
                self.log.exception('unable to set m2m identity')
        else:
            self.log.debug("skipping m2m identity notify because we don't have an auth token")
            return None

    def _sync_samples(self, batch):
        # Add samples
        samplers_updated = []
        try:
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
        except:
            self.log.exception('error syncing samples')
        return samplers_updated

    def _update_samples(self, batch, samplers_updated):
        try:
            # Remove snapshots that were successfully synced
            # Unsuccessful snapshots remain on disk, so the next sync will re-attempt them.
            for sampler_name in samplers_updated:
                sampler = self.samplers.get_sampler(sampler_name)
                try:
                    if not batch.get_result("samples.{}".format(sampler_name)):
                        self.log("failed to get sampler results '{}'".format(sampler_name))
                except Exception as e:
                    self.log.exception("error adding samples to {} ({})".format(sampler_name, e))
                else:
                    sampler.remove_snapshot()
        except:
            self.log.exception('error updating samples from sync')

    def _update_conf(self, batch):
        try:
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
        except:
            self.log.error('error updating conf in sync')

    def _sync_conf(self, batch):
        # Update conf
        try:
            conf_map = self.livesettings.contents_map
            batch.call_with_id("conf_result",
                               "device.update_conf_map",
                               conf_map=conf_map)
        except:
            self.log.exception('error syncing conf')

    def _sync_timelines(self, batch):
        # Update timeline(s)
        try:
            if self.timelines:
                for timeline in self.timelines:
                    batch.call_with_id('timeline_result_{}'.format(timeline.name),
                                       'device.add_events',
                                       name=timeline.name,
                                       events=timeline.get_events())
        except:
            self.log.exception('error syncing timelines')

    def _sync_m2m(self, batch):
        try:
            if self.m2m is not None:
                self.m2m.on_sync(batch)
        except:
            self.log.exception('error syncing m2m')

    def _sync_firmware(self, batch):
        if batch is not None and self.check_firmware:
            try:
                firmware_result = batch.get_result('firmware_result')
            except:
                self.log.exception('error getting firmware_result')
            else:
                if firmware_result['current']:
                    self.log.debug('firmware is current')
                else:
                    firmware_b64 = firmware_result['firmware']
                    device_class = firmware_result['device_class']
                    version = firmware_result['version']
                    self.log.debug("new firmware, version v{} for device class '{}'".format(version, device_class))
                    self.log.info("installing firmware v{}".format(version))
                    install_path = firmware.install_encoded(device_class,
                                                            version,
                                                            firmware_b64,
                                                            firmware_path=self.firmware_path)

                    self.log.info('firmware installed in "{}"'.format(install_path))
                    self.get_comms().restart()

    def _check_auth_token(self):
        # If we don't have an auth_token, we are waiting for permission
        if not self.auth_token and self._auth_token.startswith('file:'):
            auth_token_path = self._auth_token.split(':', 1)[-1]
            approval = self.remote.call('device.check_approval',
                                        device_class=self.device_class,
                                        subdomain=self.subdomain,
                                        serial=self.serial,
                                        name=self.name,
                                        info=self.auto_register_info)
            if approval['state'] != 'approved':
                # Device is not yet approved, can't continue with sync
                state = approval['state']
                if state == 'pending':
                    # Waiting on approval
                    self.log.debug('device approval pending...')
                else:
                    # denied
                    self.log.error('device approval {}'.format(state))
                return False
            else:
                # Device is approved. Write the auth_token.
                try:
                    os.makedirs(os.path.dirname(auth_token_path))
                except OSError:
                    pass
                try:
                    with open(auth_token_path, 'wb') as f:
                        self._auth_token = approval['auth_token']
                        f.write(self._auth_token)
                except:
                    self.log.exception('unable to write auth token')
                    # Will error out on the next command
        return True

    # Re factored this - WM
    def _sync(self):
        start = time()
        self.log.debug("syncing...")

        if not self._check_auth_token():
            return

        if not self.auth_token:
            self.log.error("sync failed -- no auth token, have you run 'dataplicity register'?")
            return

        if not os.path.exists(self.firmware_path):
            self.log.debug("no firmware installed")
            try:
                self.deploy()
            except:
                self.log.exception("unable to deploy firmware")
            raise ForceRestart("new firmware")

        samplers_updated = []
        random.seed()
        sync_id = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in xrange(12))
        batch = None
        try:
            with self.remote.batch() as batch:
                # Authenticate
                batch.call_with_id('authenticate_result',
                                   'device.check_auth',
                                   device_class=self.device_class,
                                   serial=self.serial,
                                   auth_token=self.auth_token,
                                   sync_id=sync_id)

                # Tell the server which firmware we're running
                batch.call_with_id('set_firmware_result',
                                   'device.set_firmware',
                                   version=self.current_firmware_version)

                # Check for new firmware (if required)
                if self.check_firmware:
                    batch.call_with_id('firmware_result',
                                       'device.check_firmware',
                                       current_version=self.current_firmware_version)

                samplers_updated = self._sync_samples(batch)
                self._sync_conf(batch)
                self._sync_timelines(batch)
                self._sync_m2m(batch)

            # get_result will throw exceptions with (hopefully) helpful error messages if they fail
            batch.get_result('authenticate_result')

            # If the server doesn't have the current firmware, we don't want to break the rest of the sync
            try:
                batch.get_result('set_firmware_result')
            except Exception as e:
                self.log.warning("unable to set firmware ({})".format(e))

            self._update_samples(batch, samplers_updated)
            self._update_conf(batch)

            ellapsed = time() - start
            self.log.debug('sync complete {:0.2f}s'.format(ellapsed))

        finally:
            # We have to run this code so we have a chance to update, if a bug is causing the sync handler to fail
            try:
                self._sync_firmware(batch)
            finally:
                ellapsed = time() - start
                self.log.debug('sync complete {:0.2f}s'.format(ellapsed))

    def deploy(self):
        """Deploy latest firmware"""
        self.log.info("requesting firmware...")
        with self.remote.batch() as batch:
            batch.call_with_id('register_result',
                               'device.register',
                               auth_token=self.auth_token,
                               name=self.name or self.serial,
                               serial=self.serial,
                               device_class_name=self.device_class)
            batch.call_with_id('auth_result',
                               'device.check_auth',
                               device_class=self.device_class,
                               serial=self.serial,
                               auth_token=self.auth_token)
            batch.call_with_id('firmware_result',
                               'device.get_firmware')
        try:
            batch.get_result('register_result')
        except Exception as e:
            self.log.warning(e)
        batch.get_result('auth_result')

        fw = batch.get_result('firmware_result')
        if not fw['firmware']:
            self.log.warning('no firmware available!')
            return False
        version = fw['version']

        firmware_bin = b64decode(fw['firmware'])
        firmware_file = BytesIO(firmware_bin)
        firmware_fs = ZipFS(firmware_file)

        dst_fs = OSFS(constants.FIRMWARE_PATH, create=True, dir_mode=0o775)

        firmware.install(self.device_class,
                         version,
                         firmware_fs,
                         dst_fs)

        fw_path = dst_fs.getsyspath('/')
        self.log.info("installed firmware {:010} to {}".format(version, fw_path))

        firmware.activate(self.device_class, version, dst_fs)
        self.log.info("activated firmware {:010}".format(version))


if __name__ == "__main__":
    client = Client('dataplicity.conf')
