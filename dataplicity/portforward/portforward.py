"""
	Port forwarding client

	Reads and writes to a socket, proxied over m2m

"""

from __future__ import unicode_literals
from __future__ import print_function


from ..compat import queue, py2bytes
from ..m2m import bencode, dispatcher
from . import packets
from .packets import PacketType

import socket
import weakref

from enum import IntEnum
from threading import (thread,
					   queue,
					   Event)
from threading import ThreadingError

import logging
log = logging.getLogger("dataplicity.portforward") 



class Connection(threading):
	"""Handles a single connection"""

    def __init__(self, service, connection_id, channel):
        self._service = weakref.ref(service)
        self.connection_id = connection_id

        self.channel = channel;
        
        self.dispatcher = dispatcher.Dispatcher(packets.Packet, self)
        self.q = queue.Queue()
        self.socket = None

        self.channel.set_callbacks(self.on_channel_data,
        						   self.on_channel_close,
        						   self.on_channel_control)

    @property
    def service(self):
    	return self._service()

    def run(self):
    	try:
	    	# Connect to remote host
	    	connected = self._connect()
	    	if connected is None:
	    		break

	    	while not self.close_event.is_set():
	    		try:
	    			packet_data = q.get(True, 1)
	    		except queue.Empty:
	    			continue
	    		self._on_packet(packet_data)
	    finally:
	    	self.service.on_connection_complete(self.connection_id)

    def connect(self):
    	# Connect may block, so do it in thread	
    	self.start()

    def _connect(self):
    	socket = self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    	try:
    		host = self.service.host
    		port = self.service.port
    		log.debug('connecting to %s:%s', host, port)
    		socket.connect((host, post))
    	except IOError as e:
    		log.exception('IO Error when connecting')
    		self.send(PacketType.remote_error, e.errno, py2bytes(e))
    	except:
    		pass
    		# Send an error


    def _on_packet(self, data, _decode=bencode.decode):
    	packet = _decode(data)
    	packet_type, packet_body = packet
    	self.dispatcher.dispatch(packet_type, packet_body)

    def on_channel_data(self, data):
    	"""Called by m2m channel"""
  		# We can't block here
  		# Processing is done in a thread
    	self.q.put(data)

    def on_channel_close(self, data):
    	pass

    def on_channel_control(self, data):
    	pass

    def send(self, packet_type, *args, **kwargs):
    	packet = Packet.create(packet_type, *args, **kwargs)
    	packet_bytes = packet.encode_binary()
    	self.channel.write(packet_bytes)

    @dispatcher.expose(PacketType.client_close)
    def on_client_send(self, packet_type, data):
    	try:
    		self.socket.sendall(data)
    	except IOError:
    		pass
    	except Exception:
    		pass

    @dispatcher.expose(PacketType.client_close)
    def on_client_close(self, packet_type, data):
    	pass


class Service(self):
	"""A service"""
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
	def close_event(self):
		return manager.close_event

	def connect(self, channel):
		"""Add a new connection"""
		connection_id = self._connect_index = self._connect_index + 1
		with self._lock:
			connection = self._connection[connection_id] = Connection(self, connection_id)
		connection.start()
		return connection_id

	def remove_connection(self, connection_id):
		with self._lock:
			self._connections.pop(connection_id, None)

	def on_connection_complete(self, connection_id):
		"""Called by a connection when it is finished"""
		self.remove_connection()



class PortForwardManager(object):
	"""Managed port forwarded services"""

    def __init__(self, m2m):
		self.m2m = m2m
		self._services = {}
		self._ports = {}
		
	@property
	def close_event(self):
		return self.m2m.close_event

	def get_service_on_port(self, port):
		"""Get the service on a numbbered port"""
		service_name = self._ports.get('port')
		if service_name is None:
			return None
		return self._services[service_name]

	def get_service(self, service, default=None):
		"""Get a named service"""
		return self._services.get(service, defult)

    def add_service(self, name, port, host="127.0.0.1"):
    	"""Add a service to be exposed"""
    	service = Service(name, port, host=host)
    	self._services[name] = service
    	self._ports[port] = name

    def open(self, m2m_port, service=None, port=None):
    	"""Open a port forward service"""
        if service is None and port is None:
        	raise ValueError("one of service or port is required")
        if port is not None:
        	service = self.get_service_on_port(port)
        elif service is not None:
        	service = self.get_service(service)

