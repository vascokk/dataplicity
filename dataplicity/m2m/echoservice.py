from __future__ import unicode_literals
from __future__ import print_function

import logging
log = logging.getLogger('dataplicity.m2m')

import weakref


class EchoService(object):
    """
    M2M ping service

    Technically, this is more of a 'pong' service, since it just returns data sent back to it.

    """

    def __init__(self, channel):
        # When the channel is closed, this object should go out of scope
        self._channel = weakref.ref(channel)
        channel.set_callbacks(on_data=self.on_data)

    @property
    def channel(self):
        if self._channel is None:
            return None
        return self._channel()

    def on_data(self, data):
        # Send data write back
        log.debug('echo %r', data)
        self.channel.write(data)
