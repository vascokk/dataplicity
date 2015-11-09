from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

__all__ = ["PacketType",
		   "Packet",
		   "RemoteConnect",
		   "RemoteClose",
		   "RemoteSend"]


from ..m2m.packetbase import PacketBase

from enum import IntEnum, unique

@unique
class PacketType(IntEnum):

	# ------------------------------------------
	# Packets sent from the remote side
	# ------------------------------------------

	# imcoming connection
	remote_connect = 1
	# connection has closed
	remote_close = 2
	# connection has data
	remote_send = 3


	# Packets sent from the local network
	local_close = 100
	# Data recieved from the socket
	local_recv = 101



class Packet(PacketBase):
	type = -1


class RemoteConnect(Packet):
	type = PacketType.remote_connect


class RemoteClose(Packet):
	type = PacketType.remote_close


class RemoteSend(Packet):
	type = PacketType.remote_send



