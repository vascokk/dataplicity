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
