"""JSONRPC error codes. Mirrors ErrorCodes from dataplicityapi/api"""

class ErrorCodes(object):
    """JSONRPC error codes"""
    # In functional groups of 100

    AUTH_FAILED = 1
    INVALID_DEVICE_CLASS = 2

    INIT_FAILED = 100

    UNKNOWN_DEVICE = 200

    FIRMWARE_ERROR = 300
    FIRMWARE_BADFORMAT = 301
    FIRMWARE_EXISTS = 302