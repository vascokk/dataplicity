"""

Manage packet types / encoding

"""

from __future__ import print_function
from __future__ import unicode_literals

from enum import IntEnum, unique
from dataplicity.m2m.packetbase import Packet


@unique
class PacketType(IntEnum):
    """The top level packet type"""
    # Null packet, does nothing
    null = 0

    # Client sends this to join the server
    request_join = 1

    # Client sends this to re-connect
    request_identify = 2

    # Sent by the server if request_join or request_identity was successful
    welcome = 3

    # Textual information for developer
    log = 4

    # Send a packet to another node
    request_send = 5

    # Incoming data from the server
    route = 6

    # Send the packet back
    ping = 7

    # A ping return
    pong = 8

    # Set the clients identity
    set_identity = 9

    # Open a channel
    request_open = 10

    # Close a channel
    request_close = 11

    # Close all channels
    request_close_all = 12

    # Keep alive packet
    keep_alive = 13

    # Sent by the server to notify a client that a channel has been opened
    notify_open = 14

    # Request login for privileged accounts
    request_login = 15

    notify_login_success = 16

    notify_login_fail = 17

    request_close = 18

    command_add_route = 100

# ------------------------------------------------------------
# Packet classes
# ------------------------------------------------------------


class NullPacket(Packet):
    """Probably never sent, this may be used as a sentinel at some point"""
    type = PacketType.null


class RequestJoinPacket(Packet):
    """Client requests joining the server"""
    type = PacketType.request_join


class RequestIdentifyPacket(Packet):
    """Client requests joining the server with a particular identity"""
    type = PacketType.request_identify
    attributes = [('uuid', bytes)]


class WelcomePacket(Packet):
    """Send to the client when an identity has been recorded"""
    type = PacketType.welcome


class LogPacket(Packet):
    """Log information, client may ignore"""
    type = PacketType.log


class RequestSendPacket(Packet):
    """Request to send data to a connection"""
    type = PacketType.request_send
    attributes = [('channel', int),
                  ('data', bytes)]


class RoutePacket(Packet):
    """Route data"""
    type = PacketType.route
    attributes = [('channel', int),
                  ('data', bytes)]


class PingPacket(Packet):
    """Ping packet to check connection"""
    type = PacketType.ping
    attributes = [('data', bytes)]


class PongPacket(Packet):
    """Response to Ping packet"""
    type = PacketType.pong
    attributes = [('data', bytes)]


class SetIdentityPacket(Packet):
    type = PacketType.set_identity
    attributes = [('uuid', bytes)]


class NotifyOpenPacket(Packet):
    """Let the client know a channel was opened"""
    type = PacketType.notify_open
    attributes = [('channel', int)]


class RequestLoginPacket(Packet):
    """Login for extra privileges"""
    type = PacketType.request_login
    attributes = [('username', bytes),
                  ('password', bytes)]


class NotifyLoginSuccessPacket(Packet):
    """Login success"""
    type = PacketType.notify_login_success
    attributes = [('user', bytes)]


class NotifyLoginFailPacket(Packet):
    """Login failed"""
    type = PacketType.notify_login_fail
    attributes = [('msg', bytes)]


class RequestClosePacket(Packet):
    type = PacketType.request_close


class CommandAddRoutePacket(Packet):
    type = PacketType.command_add_route
    attributes = [('uuid1', bytes),
                  ('port1', int),
                  ('uuid2', bytes),
                  ('port2', int)]

if __name__ == "__main__":
    ping_packet = PingPacket(data=b'test')
    print(ping_packet)
    print(ping_packet.as_bytes)
    print(PingPacket.from_bytes(ping_packet.as_bytes))
    print(Packet.create(PacketType.ping, data=b"test2"))
