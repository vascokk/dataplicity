class ClientException(Exception):
    pass


class ForceRestart(ClientException):
    """Tell the daemon to restart"""
    pass
