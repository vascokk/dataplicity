"""Manage a subprocess that streams to a remote side"""

from __future__ import unicode_literals
from __future__ import print_function

import sys
import os
import signal

from dataplicity.m2m import proxy

import logging
log = logging.getLogger('dataplicity.m2m')


class RemoteProcess(proxy.Interceptor):

    def __init__(self, command, channel):
        self.command = command
        self.channel = channel

        self._closed = False

        self.channel.set_callbacks(on_data=self.on_data,
                                   on_close=self.on_close)

        super(RemoteProcess, self).__init__()

    @property
    def is_closed(self):
        return self._closed

    def __repr__(self):
        return "RemoteProcess({!r}, {!r})".format(self.command, self.channel)

    def run(self):
        self.spawn([self.command])

    def on_data(self, data):
        try:
            self.stdin_read(data)
        except:
            self.channel.close()

    def on_close(self):
        self.close()

    def master_read(self, data):
        self.channel.write(data)
        super(RemoteProcess, self).master_read(data)

    def write_master(self, data):
        super(RemoteProcess, self).write_master(data)

    def close(self):
        if not self._closed:
            log.debug('sending kill signal to %r', self)
            # TODO: Implement a non-blocking kill
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
            log.debug('killed %r', self)
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
