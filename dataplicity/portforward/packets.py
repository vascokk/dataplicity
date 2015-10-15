from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

from ..m2m.packetbase import PacketBase

from enum import IntEnum, unique

@unique
class PacketType(IntEnum):

	# Packets sent from the remote side
	remote_error = 1
	remote_close = 2

	# Packets sent by the client
	client_close = 100
	client_send = 101



class Packet(PacketBase):
	type = -1


class RemoteError(Packet):
	"""One of a number of IO Errors"""
	type = PacketType.remote_error
	attributes = [('errno', int)
				  ('msg', bytes)]


class ClientClose(Packet):
	"""Client closed the connection"""
	type = PacketType.client_close

