"""Manages M2M connections."""

from __future__ import print_function
from __future__ import unicode_literals
import subprocess

from dataplicity import constants
from dataplicity.m2m import WSClient, EchoService
from dataplicity.m2m.remoteprocess import RemoteProcess

import os
import threading

import logging
log = logging.getLogger('dataplicity.m2m')


class Terminal(object):
    """Configured terminal information."""

    def __init__(self, name, command, user=None, group=None):
        self.name = name
        self.command = command
        self.user = user
        self.group = group
        self.processes = []

    def __repr__(self):
        return "<terminal '{}' command='{}'>".format(self.name, self.command)

    def _prune_closed(self):
        """Remove closed processes."""
        self.processes[:] = [process for process in self.processes if not process.is_closed]

    def launch(self, channel, size=None):
        """Launch a terminal instance."""
        if size is None:
            size = [80, 24]
        self._prune_closed()
        log.debug('opening terminal %s', self.name)
        remote_process = None
        try:
            remote_process = RemoteProcess(self.command,
                                           channel,
                                           user=self.user,
                                           group=self.group,
                                           size=size)
        except:
            log.exception("error launching terminal process '%s'", self.command)
            if remote_process is not None:
                try:
                    remote_process.close()
                except:
                    pass
        else:
            self.processes.append(remote_process)
            process_thread = threading.Thread(target=remote_process.run)
            process_thread.start()
            log.info("launched remote process %r over %r", self, channel)

    def close(self):
        self._prune_closed()
        for process in self.processes:
            log.debug('closing %r', self)
            try:
                if not process.is_closed:
                    log.debug('closing %r', self)
                    process.close()
            except:
                log.exception('error closing %s', process)
        del self.processes[:]


class AutoConnectThread(threading.Thread):
    """Maintains a terminal connection."""

    def __init__(self, manager, url, identity=None):
        self.manager = manager
        self.url = url
        self._m2m_client = None
        self._identity = identity
        self.lock = threading.RLock()
        self.exit_event = threading.Event()
        threading.Thread.__init__(self)
        self.daemon = True

    @property
    def identity(self):
        with self.lock:
            return self._identity

    @property
    def m2m_client(self):
        with self.lock:
            return self._m2m_client

    def close(self):
        """Close and end the auto-connect thread."""
        self.exit_event.set()

    def start_connect(self):
        with self.lock:
            log.debug('connecting to %s', self.url)
            self._m2m_client = M2MClient(self.url, log=log, uuid=self._identity)
            self._m2m_client.set_manager(self.manager)
            self._m2m_client.connect(wait=False)

    def run(self):
        # Immediately start the connect process
        self.start_connect()

        while 1:
            # Get the identity, and tell the server about it
            identity = self._identity = self.m2m_client.wait_ready(10)
            self.manager.set_identity(identity)

            with self.lock:
                # If we aren't connected, kick off the connect process
                if not identity or self.m2m_client.is_closed:
                    self.start_connect()

            # We are connected, so wait on the exit event
            # The timeout prevents hammering of the server
            if self.exit_event.wait(5.0):
                break

        # Tell the server we are no longer connected to m2m
        self.manager.set_identity(None)
        with self.lock:
            if self.m2m_client is not None:
                self.m2m_client.close()


class M2MClient(WSClient):
    """Client for M2M server."""

    def set_manager(self, manager):
        self._manager = manager

    @property
    def manager(self):
        return getattr(self, '_manager', None)

    def on_instruction(self, sender, data):
        self.manager.on_instruction(sender, data)

    def on_close(self, app):
        super(M2MClient, self).on_close(app)
        self.manager.on_client_close()


class M2MManager(object):
    """Manages M2M Services."""

    def __init__(self, client, url, identity=None):
        self.client = client
        self.url = url
        self.identity = identity
        self.terminals = {}
        self.notified_identity = None
        self.connect_thread = AutoConnectThread(self, url, identity=self.identity)
        self.connect_thread.start()

    @property
    def m2m_client(self):
        return self.connect_thread.m2m_client

    @classmethod
    def init_from_conf(cls, client, conf):
        # m2m is now on by default
        enabled = conf.get('m2m', 'enabled', 'yes') == 'yes'
        if not enabled:
            log.debug('m2m is not enabled')
            return None

        url = conf.get('m2m', 'url', constants.M2M_URL)
        if url is None:
            log.debug('m2m not used')
            return None
        log.debug('m2m url is %s', url)

        identity = conf.get('m2m', 'identity', None)
        if identity is not None:
            log.debug('m2m identity is %s (works with internal development server only)', identity)

        manager = cls(client, url, identity=identity)

        for section, name in conf.qualified_sections('terminal'):
            cmd = conf.get(section, 'command', os.environ.get('SHELL', None))
            if cmd is None:
                cmd = "bash"
            user = conf.get(section, 'user', None)
            group = conf.get(section, 'group', None)
            manager.add_terminal(name, cmd, user=user, group=group)

        return manager

    def on_client_close(self):
        for terminal in self.terminals.values():
            terminal.close()

    def set_identity(self, identity):
        """Set the m2m identity, and also notifies the dataplicity server if required."""
        self.identity = identity
        if identity and identity != self.notified_identity:
            self.notified_identity = self.client.set_m2m_identity(identity)

    def on_sync(self, batch):
        """Called by sync, so it can inject commands in to the batch request."""
        # Send the m2m identity on every sync
        # This shouldn't be neccesary, but could mitigate any screw ups server side
        if self.identity:
            log.debug('syncing m2m identity (%s)', self.identity)
            batch.notify('m2m.associate', identity=self.identity)

    def close(self):
        log.debug('m2m manager close')
        self.connect_thread.close()
        if self.m2m_client is not None:
            self.m2m_client.close()

    def add_terminal(self, name, remote_process, user=None, group=None):
        log.debug("adding terminal '%s' %s", name, remote_process)
        self.terminals[name] = Terminal(name, remote_process, user=user, group=group)

    def get_terminal(self, name):
        return self.terminals.get(name, None)

    def on_instruction(self, sender, data):
        log.debug("instruction %r from %s", data, sender)
        action = data['action']
        if action == 'sync':
            self.client.sync()
        elif action == 'open-terminal':
            port = data['port']
            terminal_name = data['name']
            size = data.get('size', None)
            self.open_terminal(terminal_name, port, size=size)
        elif action == "open-keyboard":
            port = data['port']
            keyboard_name = data['name']
            self.open_keyboard(keyboard_name, port)
        elif action == "open-buttons":
            port = data['port']
            buttons_group = data['name']
            self.open_buttons(buttons_group, port)
        elif action == "open-echo":
            port = data['port']
            self.open_echo_service(port)
        elif action == 'open-portforward':
            service = data['service']
            route = data['route']
            self.open_portforward(service, route)
        elif action == 'reboot-device':
            log.debug('reboot requested')
            self.reboot()

    def open_terminal(self, name, port, size=None):
        terminal = self.get_terminal(name)
        if terminal is None:
            log.warning("no terminal called '%s'", name)
            return
        terminal.launch(self.m2m_client.get_channel(port), size=size)

    def open_keyboard(self, name, port):
        self.client.rc.open_keyboard(name, self.m2m_client.get_channel(port))

    def open_buttons(self, name, port):
        self.client.rc.open_buttons(name, self.m2m_client.get_channel(port))

    def open_echo_service(self, port):
        log.debug('opening echo service on m2m port %s', port)
        EchoService(self.m2m_client.get_channel(port))

    def open_portforward(self, service, route):
        self.client.port_forward.open_service(service, route)

    def reboot(self):
        """Initiate a reboot."""
        # TODO: consider initiating a graceful shutdown of dpcore that ends in a rebooot
        command = '/usr/bin/sudo /sbin/reboot'
        # Why not subprocess.call? Because it will block this process and prevent graceful exit!
        pid = subprocess.Popen(command.split()).pid
        log.debug('opened reboot process %s', pid)
