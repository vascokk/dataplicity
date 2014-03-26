
# import socket
# import fcntl
# import struct


# def _get_mac(ifname):
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack(b'256s', ifname[:15]))
#     return ''.join(['%02x' % ord(char) for char in info[18:24]])


# def get_default_serial():
#     """Get a default serial number from the mac address of the first network adapter"""
#     return _get_mac(b'eth0')

from uuid import getnode


def get_default_serial():
    serial = "{:016X}".format(getnode()).lower()
    return serial


if __name__ == "__main__":
    print get_default_serial()
