from __future__ import unicode_literals
from __future__ import print_function

"""JSONRPC error codes. Mirrors ErrorCodes from dataplicityapi/api"""


class ErrorCodes(object):
    """JSONRPC error codes"""
    # In functional groups of 100
    AUTH_FAILED = 1
    INVALID_DEVICE_CLASS = 2
    INVALID_DEVICE = 3

    INIT_FAILED = 100

    UNKNOWN_DEVICE = 200

    FIRMWARE_ERROR = 300
    FIRMWARE_BADFORMAT = 301
    FIRMWARE_EXISTS = 302
    FIRMWARE_MISSING = 303

    UI_INVALID = 400
