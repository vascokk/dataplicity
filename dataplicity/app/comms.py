import socket


class CommsError(Exception):
    pass


class Comms(object):
    """Communicates with the dataplicity daemon"""

    def __init__(self, ip='127.0.0.1', port=8888):
        self.ip = ip
        self.port = port

    def __call__(self, command):
        response = []
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.ip, self.port))
            sock.sendall("%s\n" % command.upper())
            append_char = response.append
            while 1:
                try:
                    data = sock.recv(1)
                except socket.error:
                    break
                if data in ('\n', ''):
                    break
                append_char(data)
            return ''.join(response)

        finally:
            if sock is not None:
                sock.close()
        return True

    def sync(self):
        return self('SYNC')

    def restart(self):
        return self('RESTART')

    def stop(self):
        return self('STOP')

    def status(self):
        try:
            return True, self('STATUS')
        except CommsError:
            return False, ''