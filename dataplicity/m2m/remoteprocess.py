"""Manage a subprocess that streams to a remote side"""

from __future__ import unicode_literals
from __future__ import print_function

import sys

from dataplicity.m2m import proxy


class RemoteProcess(proxy.Interceptor):

    def __init__(self, command, channel):
        self.command = command
        self.channel = channel

        self._closed = False

        self.channel.set_data_callback(self.on_data)

        super(RemoteProcess, self).__init__()

    def run(self):
        self.spawn([self.command])

    def on_data(self, data):
        try:
            self.stdin_read(data)
        except:
            self.channel.close()

    def master_read(self, data):
        self.channel.write(data)
        super(RemoteProcess, self).master_read(data)

    def write_master(self, data):
        super(RemoteProcess, self).write_master(data)

    def close(self):
        if not self._closed:
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


if __name__ == "__main__":
    import sys

    import logging
    logging.basicConfig(level=logging.CRITICAL)

    from wsclient import WSClient
    client = WSClient('wss://home.willmcgugan.com:8888/m2m/',
                      uuid=b"5ad1e682-6a74-11e4-8535-0f38840b9aea")
    client.start()


    print("connecting")
    uuid = client.wait_ready()

    #sys.exit()

    if uuid is None:
        print("failed to connect")
        sys.exit(-1)

    print("{{{uuid}}}".format(uuid=uuid))

    raw_input('Hit return when ready')

    try:

        channel = client.get_channel(1)
        remote_process = RemoteProcess('/bin/sh', channel)
        remote_process.spawn()
        print("Exit remote process")

    finally:

        client.close()
