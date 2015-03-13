from __future__ import unicode_literals
from __future__ import print_function

import os
import io


class AtomicWriter(object):
    """Context manager to perform atomic writes"""

    def __init__(self, path, mode='w'):
        self.path = path
        self.mode = mode
        self.tmp_path = path + '~'
        self._f = None

    def __enter__(self):
        self._f = io.open(self.tmp_path, self.mode)
        return self._f

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            if self._f is not None:
                self._f.flush()
                os.fsync(self._f.fileno())
                self._f.close()
                self._f = None
                os.rename(self.tmp_path, self.path)
        else:
            if self._f is not None:
                self._f.close()


def open(path, mode='w'):
    """Replaces builtin, but ensures atomic write"""
    return AtomicWriter(path, mode=mode)


if __name__ == "__main__":
    with open('test.txt') as f:
        f.write('Hello, World!\n')
