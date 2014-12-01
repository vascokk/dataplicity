"""
Manages M2M connections

"""

from __future__ import print_function
from __future__ import unicode_literals


from dataplicity.m2m import WSClient

import os
import logging
log = logging.getLogger('dataplicity.m2m')


class RemoteProcess(object):
    def __init__(self, name, command):
        self.name = name
        self.command = command


class M2MClient(WSClient):

    def set_manager(self, manager):
        self._manager = manager

    @property
    def manager(self):
        return getattr(self, '_manager', None)

    def on_instruction(self, sender, data):
        self.manager.on_instruction(sender, data)


class M2MManager(object):

    def __init__(self, client, url):
        self.client = client
        self.url = url
        self.remote = {}
        client = self.m2m_client = M2MClient(url, log=log)
        client.set_manager(self)
        client.connect(wait=False)

    # def connect(self):
    #     log.debug('connecting to m2m server %s', self.url)
    #     self.identity = self.m2m_client.connect(3)
    #     if self.identity is None:
    #         log.error('connect failed')
    #     else:
    #         log.info('m2m identity {%s}'.format(self.identity))

    @classmethod
    def init_from_conf(cls, client, conf):
        url = conf.get('m2m', 'url', None)
        if url is None:
            log.debug('m2m not used')
            return None

        manager = cls(client, url)

        for section, name in conf.qualified_sections('terminal'):
            cmd = conf.get(section, 'command', os.environ.get('SHELL', None))
            remote_process = RemoteProcess(name, cmd)
            manager.add_remote_process(name, remote_process)

    def close(self):
        if self.m2m_client is not None:
            self.m2m_client.close()

    def add_remote_process(self, name, remote_process):
        self.remote[name] = remote_process

    def on_instruction(self, sender, data):
        log('instruction: %s %r', sender, data)
