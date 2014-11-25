"""
Manages M2M connections

"""

from __future__ import print_function
from __future__ import unicode_literals


from dataplicity.m2m import WSClient

import os


class RemoteProcess(object):
    def __init__(self, name, command):
        self.name = name
        self.command = command


class M2MManager(object):

    def __init__(self, url):
        self.url = url
        self.remote = {}
        self.m2m_client = WSClient(url)

    @classmethod
    def init_from_conf(cls, client, conf):
        url = conf.get('m2m', 'url', None)
        if url is None:
            return cls(url)

        manager = cls(url)

        for section, name in conf.qualified_sections('remote'):
            cmd = conf.get(section, 'command', os.environ.get('SHELL', None))
            remote_process = RemoteProcess(name, cmd)
            manager.add_Remote_process(name, remote_process)

    def close(self):
        self.m2m_client.close()

    def add_remote_process(self, name, remote_process):
        self.remote[name] = remote_process
