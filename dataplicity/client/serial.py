from __future__ import unicode_literals
from __future__ import print_function

from uuid import getnode


def get_default_serial():
    serial = "{:016X}".format(getnode()).lower()
    return serial


if __name__ == "__main__":
    print(get_default_serial())
