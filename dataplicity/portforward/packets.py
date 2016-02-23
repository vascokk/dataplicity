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

    # incoming connection
    remote_connect = 1
    # connection has closed
    remote_close = 2
    # connection has data
    remote_send = 3

    # Connection on the local side established
    local_connect = 100
    # Connection on the local side closed
    local_close = 101
    # Data received from the socket
    local_recv = 102


class Packet(PacketBase):
    type = -1


class RemoteConnect(Packet):
    type = PacketType.remote_connect


class RemoteClose(Packet):
    type = PacketType.remote_close


class RemoteSend(Packet):
    type = PacketType.remote_send
    attributes = [('data', bytes)]


class LocalConnect(Packet):
    type = PacketType.local_connect


class LocalClose(Packet):
    type = PacketType.local_close


class LocalRecv(Packet):
    type = PacketType.local_recv
    attributes = [('data', bytes)]
