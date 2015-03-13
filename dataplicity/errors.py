from __future__ import unicode_literals
from __future__ import print_function

"""Errors thrown by the dataplicity module"""


class DataplicityError(Exception):
    """A catch-all for dataplicity errors"""


class ConfigError(DataplicityError):
    """Thrown when there is a problem reading config information"""
    pass


class StartupError(DataplicityError):
    pass


class InvalidSequence(DataplicityError):
    """Client requested an invalid sequence"""
    pass
