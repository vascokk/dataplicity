from __future__ import unicode_literals
from __future__ import print_function


class ClientException(Exception):
    pass


class ForceRestart(ClientException):
    """Tell the daemon to restart"""
    pass
