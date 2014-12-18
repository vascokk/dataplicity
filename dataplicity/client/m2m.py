"""
Manages M2M connections

"""

from __future__ import print_function
from __future__ import unicode_literals

from dataplicity import constants
from dataplicity.m2m import WSClient
from dataplicity.m2m.remoteprocess import RemoteProcess

import os
import threading

import logging
log = logging.getLogger('dataplicity.m2m')


class Terminal(object):
    def __init__(self, name, command):
        self.name = name
        self.command = command
        self.processes = []

    def __repr__(self):
        return "<terminal '{}' command='{}'>".format(self.name, self.command)

    def launch(self, channel):
        log.debug('opening terminal %s', self.name)
        remote_process = None
        try:
            remote_process = RemoteProcess(self.command, channel)
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
        for process in self.processes:
            log.debug('closing %r', self)
            try:
                process.close()
            except:
                log.exception('error in process close')


class M2MClient(WSClient):

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

    def __init__(self, client, url):
        self.client = client
        self.url = url
        self.terminals = {}
        self.identity = ''
        client = self.m2m_client = M2MClient(url, log=log)
        client.set_manager(self)

    def connect(self):
        log.debug('connecting to %s', self.url)
        self.m2m_client.connect(timeout=3)

    @classmethod
    def init_from_conf(cls, client, conf):
        enabled = conf.get('m2m', 'enabled', 'no') == 'yes'
        if not enabled:
            log.debug('m2m is not enabled')
            return None

        url = conf.get('m2m', 'url', constants.M2M_URL)
        if url is None:
            log.debug('m2m not used')
            return None
        log.debug('m2m url is %s', url)

        manager = cls(client, url)

        for section, name in conf.qualified_sections('terminal'):
            cmd = conf.get(section, 'command', os.environ.get('SHELL', None))
            if cmd is None:
                cmd = "sh"
            manager.add_terminal(name, cmd)
        manager.connect()

        return manager

    def on_client_close(self):
        self.close()
        for terminal in self.terminals.values():
            terminal.close()

    def check_connect(self):
        """Attempt re-connect if we are not connected"""
        try:
            if self.m2m_client.is_closed:
                log.debug('re-connecting to m2m server %s', self.url)
                client = self.m2m_client = M2MClient(self.url, log=log)
                client.set_manager(self)
                try:
                    client.connect(wait=False)
                except:
                    log.exception('re-connect failed')
        except:
            log.exception('error in check_connect')

    def on_sync(self, batch):
        """Called by sync, so it can inject commands in to the batch request"""
        self.check_connect()
        try:
            identity = self.m2m_client.wait_ready(3)
            if identity != self.identity:
                log.debug('notifying server of m2m identity {%s}', identity)
                batch.notify('m2m.associate',
                             identity=identity or '')
                self.identity = identity
        except Exception:
            # We can't risk breaking the sync
            log.exception('error in M2MManager.on_sync')

    def close(self):
        if self.m2m_client is not None:
            self.m2m_client.close()
        self.identity = ''

    def add_terminal(self, name, remote_process):
        log.debug("adding terminal '%s' %s", name, remote_process)
        self.terminals[name] = Terminal(name, remote_process)

    def get_terminal(self, name):
        return self.terminals.get(name, None)

    def on_instruction(self, sender, data):
        action = data['action']
        if action == 'open-terminal':
            port = data['port']
            terminal_name = data['name']
            self.open_terminal(terminal_name, port)

    def open_terminal(self, name, port):
        terminal = self.get_terminal(name)
        if terminal is None:
            log.warning("no terminal called '%s'", name)
            return
        terminal.launch(self.m2m_client.get_channel(port))
