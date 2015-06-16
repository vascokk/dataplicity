from __future__ import unicode_literals
from __future__ import print_function

import os
import os.path


def find_conf():
    """Finds a dataplicity.conf file in the current working directory, or ancestors"""
    path = os.path.abspath(os.path.expanduser(os.getcwd()))
    while path not in ('', '/'):
        conf_path = os.path.join(path, 'dataplicity.conf')
        if os.path.exists(conf_path):
            return conf_path
        path = os.path.dirname(path)
    return None


def parse_lines(s):
    """Split a setting in to a list"""
    return [l.strip() for l in s.splitlines() if l.strip()]


def resolve_value(value):
    """resolve a value which may have a file: prefix"""
    if value is None:
        return value
    value = value.strip()
    if value.startswith('file:'):
        path = value.split(':', 1)[-1]
        try:
            with open(path, 'rt') as f:
                value = f.read().strip()
        except IOError:
            value = None

    return value
