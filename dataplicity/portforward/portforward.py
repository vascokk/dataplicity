"""
Port forwarding client

Reads and writes to a socket, proxied over m2m

"""

from __future__ import unicode_literals
from __future__ import print_function


from ..m2m import bencode, dispatcher
from . import packets

import socket
import weakref
import threading
import select


import logging
log = logging.getLogger("dataplicity")


class Connection(threading.Thread):
    """Handles a single remote controlled TCP/IP connection"""

    # Bytes to read at-a-time
    BUFFER_SIZE = 1024 * 8

    def __init__(self, service, connection_id, channel):
        super(Connection, self).__init__()
        self._service = weakref.ref(service)
        self.connection_id = connection_id
        self.channel = channel

        self._lock = threading.RLock()
        self.dispatcher = dispatcher.Dispatcher(packets.Packet, self)
        self.socket = None
        self.read_buffer = []  # For data received before we connected

        self.channel.set_callbacks(self.on_channel_data,
                                   self.on_channel_close,
                                   self.on_channel_control)

    @property
    def service(self):
        return self._service()

    @property
    def close_event(self):
        return self.service.close_event

    @property
    def remote(self):
        return "{}:{}".format(self.service.host, self.service.port)

    def run(self):
        log.debug("connection started")
        try:
            # Connect to remote host
            connected = self._connect()
            if not connected:
                return

            log.debug("entered recv loop")

            self._flush_buffer()
            # Read all the data we can and write it to the channel
            # TODO: Rework this loop to not use the timeout
            while not self.close_event.is_set():
                readable, _, _ = select.select([self.socket], [], [], 1.0)
                if readable:
                    try:
                        data = self.socket.recv(self.BUFFER_SIZE)
                    except:
                        log.exception('error in recv')
                        break
                    else:
                        if data:
                            self.channel.write(data)
                        else:
                            break
        finally:
            log.debug("left recv loop")
            self.channel.close()
            self.service.on_connection_complete(self.connection_id)
            self._close_socket()

    def _close_socket(self):
        """Shutdown the socket"""
        if self.socket is not None:
            # try:
            #     self.socket.shutdown(socket.SHUT_RDWR)
            # except:
            #     log.exception('error shutting down socket')
            try:
                self.socket.close()
            except:
                log.exception('error closing socket')

    def connect(self):
        # Connect may block, so do it in thread
        self.start()

    def _connect(self):
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            host = self.service.host
            port = self.service.port
            log.debug('connecting to %s', self.remote)
            _socket.connect((host, port))
            _socket.setblocking(False)
        except IOError:
            log.exception('IO Error when connecting')
            # self.send(PacketType.remote_error, e.errno, py2bytes(e))
            return False
        except:
            log.exception('error connecting')
            return False
        else:
            log.debug("connected to %s", self.remote)
            self.socket = _socket
            self._flush_buffer()
            return True
        return False

    def _on_packet(self, data, _decode=bencode.decode):
        packet = _decode(data)
        packet_type, packet_body = packet
        self.dispatcher.dispatch(packet_type, packet_body)

    def on_channel_data(self, data):
        """Called by m2m channel"""
        log.debug("got data %r", data)
        with self._lock:
            self.read_buffer.append(data)
            self._flush_buffer()

    def _flush_buffer(self):
        with self._lock:
            if self.socket is not None:
                data = b''.join(self.read_buffer)
                del self.read_buffer[:]
                self.socket.sendall(data)

    def on_channel_close(self):
        log.debug('channel close')
        if self.socket is not None:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                log.exception('error shutting down socket in on_channel_close')

    def on_channel_control(self, data):
        log.debug('channel control %r', data)


class Service(object):
    """A service defines a host and port to forward"""
    def __init__(self, manager, name, port, host="127.0.0.1"):
        self._manager = weakref.ref(manager)
        self.name = name
        self.port = port
        self.host = host
        self._connect_index = 0
        self._connections = {}
        self._lock = threading.RLock()

    def __repr__(self):
        return "<service {}:{} '{}'>".format(self.host, self.port, self.name)

    @property
    def manager(self):
        return self._manager()

    @property
    def m2m(self):
        return self.manager.m2m

    @property
    def close_event(self):
        return self.manager.close_event

    def connect(self, port_no):
        """Add a new connection"""
        log.debug('new %r connection on port %s', self, port_no)
        with self._lock:
            connection_id = self._connect_index = self._connect_index + 1
            channel = self.m2m.m2m_client.get_channel(port_no)
            connection = self._connections[connection_id] = Connection(self, connection_id, channel)
        connection.start()
        return connection_id

    def remove_connection(self, connection_id):
        with self._lock:
            self._connections.pop(connection_id, None)

    def on_connection_complete(self, connection_id):
        """Called by a connection when it is finished"""
        self.remove_connection(connection_id)


class PortForwardManager(object):
    """Managed port forwarded services"""

    def __init__(self, client):
        self._client = weakref.ref(client)
        self._services = {}
        self._ports = {}
        self._close_event = threading.Event()

    @property
    def client(self):
        return self._client()

    @property
    def m2m(self):
        return self.client.m2m if self.client else None

    @classmethod
    def init_from_conf(cls, client, conf):
        """Initialise PF from dataplicity.conf"""
        manager = PortForwardManager(client)
        for section, name in conf.qualified_sections('portforward'):
            if not conf.get_bool(section, 'enabled', True):
                continue
            port = conf.get_integer(section, 'port', 80)
            manager.add_service(name, port)
        return manager

    @property
    def close_event(self):
        return self._close_event

    def on_client_close(self):
        """M2M client closed"""
        log.debug('m2m exited')

    def get_service_on_port(self, port):
        """Get the service on a numbered port"""
        service_name = self._ports.get('port')
        if service_name is None:
            return None
        return self._services[service_name]

    def get_service(self, service, default=None):
        """Get a named service"""
        return self._services.get(service, default)

    def add_service(self, name, port, host="127.0.0.1"):
        """Add a service to be exposed"""
        service = Service(self, name, port, host=host)
        self._services[name] = service
        self._ports[port] = name
        log.debug("added port forward service '%s' on port %s", name, port)

    def open_service(self, service, route):
        log.debug('opening service %s on %r', service, route)
        node1, port1, node2, port2 = route
        self.open(port2, service)

    def open(self, m2m_port, service=None, port=None):
        """Open a port forward service"""
        if service is None and port is None:
            raise ValueError("one of service or port is required")
        if port is not None:
            service = self.get_service_on_port(port or 80)
        elif service is not None:
            service = self.get_service(service)
        service.connect(m2m_port)
