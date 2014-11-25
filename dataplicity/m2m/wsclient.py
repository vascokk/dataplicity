from __future__ import unicode_literals
from __future__ import print_function

import websocket

from dataplicity.m2m import bencode
from dataplicity.m2m import packets
from dataplicity.m2m.dispatcher import Dispatcher, expose
from dataplicity.m2m.packets import PacketType
from dataplicity.m2m.packetbase import Packet
from dataplicity.m2m.compat import text_type

from collections import deque
import sys
import socket
import threading
import ssl

import logging
log = logging.getLogger('m2m.client')


class ClientError(Exception):
    pass


class ChannelFile(object):

    def __init__(self, client, channel_no):
        self.client = client
        self.channel_no = channel_no

    def write(self, data):
        sys.stdout.write(data)
        self.client.channel_write(self.channel_no, data)

    def fileno(self):
        return None


class Channel(object):
    """An interface to a channel"""

    def __init__(self, client, number):
        self.client = client
        self.number = number

        self._data_callback = None
        self._lock = threading.RLock()
        self.deque = deque()
        self._data_event = threading.Event()

    def __repr__(self):
        return "<channel {}>".format(self.number)

    def on_data(self, data):
        """On incoming data"""
        with self._lock:
            self.deque.append(data)
            self._data_event.set()
        if self._data_callback is not None:
            self._data_callback(data)

    def set_data_callback(self, callback):
        self._data_callback = callback

    @property
    def size(self):
        with self._lock:
            return sum(len(b) for b in self.deque)

    def __nonzero__(self):
        return self._data_event.is_set()

    def read(self, count, timeout=None, block=False):
        """Read up to `count` bytes"""
        incoming_bytes = []
        bytes_remaining = count

        # Block until data

        if block:
            if not self._data_event.wait(timeout):
                return b''

        with self._lock:
            # Data may be spread accross multiple / partial messages
            while self.deque and bytes_remaining:
                head = self.deque[0]
                read_bytes = min(bytes_remaining, len(head))
                incoming_bytes.append(head[:read_bytes])
                bytes_left = head[read_bytes:]
                bytes_remaining -= read_bytes
                if not bytes_left:
                    self.deque.popleft()
                else:
                    self.deque[0] = bytes_left
            if not self.deque:
                self._data_event.clear()

        return b''.join(incoming_bytes)

    def write(self, data):
        assert isinstance(data, bytes), "data must be bytes"
        with self._lock:
            self.client.channel_write(self.number, data)

    def get_file(self):
        return ChannelFile(self.client, self.number)


class ThreadedDispatcher(threading.Thread, Dispatcher):
    def __init__(self, **kwargs):
        # Why didn't super work here?
        threading.Thread.__init__(self)
        Dispatcher.__init__(self, Packet, log=kwargs.get('log'))


class WSClient(ThreadedDispatcher):

    def __init__(self, url, uuid=None, log=None, **kwargs):
        self.url = url
        kwargs['on_open'] = self.on_open
        kwargs['on_message'] = self.on_message
        kwargs['on_error'] = self.on_error
        kwargs['on_close'] = self.on_close
        self.kwargs = kwargs

        self._started = False
        self._closed = False
        self.identity = uuid
        self.channels = {}

        self.ready_event = threading.Event()
        self.close_event = threading.Event()

        super(WSClient, self).__init__(log=log)
        self.daemon = True

        self.app = websocket.WebSocketApp(self.url,
                                          **self.kwargs)

    def __repr__(self):
        return 'WSClient({!r})>'.format(self.url)

    def __enter__(self):
        self.wait_ready()
        return self

    def __exit__(self, *args, **kwargs):
        if not self.close_event.is_set():
            self.send(PacketType.request_close)
            self.close_event.wait(3)

    def connect(self):
        self.start()
        return self.wait_ready()

    def get_channel(self, channel_no):
        # TODO: Create channels in response to packets
        if channel_no not in self.channels:
            self.channels[channel_no] = Channel(self, channel_no)
        return self.channels[channel_no]

    def run(self):
        self._started = True
        self.app.run_forever(sockopt=((socket.SOL_SOCKET, socket.SO_REUSEPORT, 1),
                                      (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)),
                             sslopt={"cert_reqs": ssl.CERT_NONE})

    def close(self, timeout=5):
        if not self.close_event.is_set():
            self.send(PacketType.request_close)
            self.close_event.wait(timeout)
        self._started = False

    def wait_ready(self):
        """Wait until the server is ready, and return identity"""
        while 1:
            if self.ready_event.wait(1):
                break
        return self.identity

    def wait_close(self):
        while 1:
            if self.close_event.wait(1):
                break

    def send(self, packet, *args, **kwargs):
        """Send a packet. Will encode if necessary."""
        if isinstance(packet, (bytes, text_type)):
            packet = PacketType[packet].value
        if isinstance(packet, (PacketType, int)):
            packet = Packet.create(packet, *args, **kwargs)
        log.debug("sending %r", packet)

        packet_bytes = packet.encode_binary()
        self.send_bytes(packet_bytes)

    def send_bytes(self, packet_bytes):
        """Send bytes over the websocket"""
        self.app.sock.send_binary(packet_bytes)

    def on_open(self, app):
        """Called when WS is opened"""
        log.debug("websocket opened")
        if self.identity is None:
            self.send(PacketType.request_join)
        else:
            self.send(PacketType.request_identify, uuid=self.identity)

    def on_message(self, app, data):
        """a WS message"""
        packet = bencode.decode(data)
        self.on_packet(packet)

    def on_error(self, app, error):
        """Called on WS error"""
        self.ready_event.set()
        self.log.error(text_type(error))

    def on_close(self, app):
        self.log.debug('connection closed by peer')
        self.close_event.set()
        self.ready_event.set()
        self.closed = True

    def on_packet(self, packet):
        packet_type = packets.PacketType(packet[0])
        packet_body = packet[1:]
        self.dispatch(packet_type, packet_body)

    def channel_write(self, channel, data):
        self.send(PacketType.request_send, channel=channel, data=data)

    # --------------------------------------------------------
    # Packet handlers
    # -------------------------------------------------------

    @expose(PacketType.set_identity)
    def handle_set_identity(self, packet_type, identity):
        self.identity = identity
        self.log.debug('setting identity to %r', self.identity)

    @expose(PacketType.welcome)
    def handle_welcome(self, packet_type):
        self.ready_event.set()

    @expose(PacketType.route)
    def handle_route(self, packet_type, channel, data):
        channel = self.get_channel(channel)
        channel.on_data(data)

    @expose(PacketType.notify_open)
    def on_notify_open(self, packet_type, channel_no):
        log.debug('channel {} opened'.format(channel_no))

    @expose(PacketType.notify_login_success)
    def on_login_success(self, packet_type, user):
        self.user = user
        log.debug('logged in as %s', user)


if __name__ == "__main__":

    import logging
    logging.basicConfig(level=logging.DEBUG)

    client = WSClient('wss://127.0.0.1:8888/m2m/')

    client.start()

    import time
    try:
        while 1:
            time.sleep(0.1)
    finally:
        client.close()
