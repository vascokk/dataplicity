from __future__ import unicode_literals
from __future__ import print_function

from dataplicity import constants
from dataplicity.client import settings
from dataplicity.compat import PY2

if PY2:
    from ConfigParser import SafeConfigParser
else:
    from configparser import SafeConfigParser

from fs.utils import copyfile, copydir
from fs.errors import ResourceNotFoundError
from fs.zipfs import ZipFS
from fs.osfs import OSFS

import os
import base64
from os.path import basename, join
from fnmatch import fnmatch
from logging import getLogger
from io import BytesIO

log = getLogger('dataplicity')


DEFAULT_FIRMWARE_CONF = """
[firmware]
version = 1
exclude = *.pyc
    __*__
    .*
    .hg
    .git

"""


def _get_list(value):
    """Get a list of values from a setting"""
    return [line.strip() for line in value.split('\n')]


def get_conf(src_fs):
    """Get the conf from a firmware fs"""
    cfg = SafeConfigParser()
    with src_fs.open('dataplicity.conf') as f:
        cfg.readfp(f)
    return cfg


def get_version(src_fs):
    """Get a version number from the firmware"""
    if not src_fs.exists('firmware.conf'):
        src_fs.setcontents('firmware.conf', DEFAULT_FIRMWARE_CONF)
    cfg = SafeConfigParser()
    with src_fs.open('firmware.conf') as f:
        cfg.readfp(f)
    version = int(cfg.get('firmware', 'version'))
    return version


def bump(src_fs):
    """Increment the firmware version stored in firmware.conf"""
    version = int(get_version(src_fs))
    new_version = version + 1
    cfg = SafeConfigParser()
    with src_fs.open('firmware.conf') as f:
        cfg.readfp(f)
    cfg.set('firmware', 'version', str(new_version))
    with src_fs.open('firmware.conf', 'wb') as f:
        cfg.write(f)
    print("firmware version bumped to {}".format(new_version))
    return new_version


def build(src_fs, dst_fs):
    """Build a firmware"""
    if not src_fs.exists('firmware.conf'):
        src_fs.setcontents('firmware.conf', DEFAULT_FIRMWARE_CONF)

    cfg = SafeConfigParser()
    with src_fs.open('firmware.conf') as f:
        cfg.readfp(f)

    version = int(cfg.get('firmware', 'version'))
    exclude = _get_list(cfg.get('firmware', 'exclude'))

    def wildcard(path):
        return not any(fnmatch(basename(path), wildcard) for wildcard in exclude)

    for file_path in src_fs.walkfiles(wildcard=wildcard, dir_wildcard=wildcard):
        copyfile(src_fs, file_path, dst_fs, file_path)

    return version


def install(device_class, version, firmware_fs, dst_fs):
    """Install a firmware"""
    dst_path = join(device_class, str(version))
    if not dst_fs.exists(dst_path):
        dst_fs.makedir(dst_path, allow_recreate=True, recursive=True)
    install_fs = dst_fs.opendir(dst_path)
    copydir(firmware_fs, install_fs)
    install_path = dst_fs.getsyspath(dst_path)

    try:
        os.chmod(install_path, 0o0775)
    except:
        pass

    # Return install_path
    return install_path


def install_encoded(device_class, version, firmware_b64, activate_firmware=True, firmware_path=None):
    """Install firmware from a b64 encoded zip file"""
    # TODO:  implement this in a less memory hungry way
    # decode from b64
    firmware_bin = base64.b64decode(firmware_b64)
    # Make a file-like object
    firmware_file = BytesIO(firmware_bin)
    # Open zip
    firmware_fs = ZipFS(firmware_file)
    # Open firmware dir
    dst_fs = OSFS(firmware_path or constants.FIRMWARE_PATH, create=True, dir_mode=0o755)
    # Install
    install_path = install(device_class, version, firmware_fs, dst_fs)
    # Move symlink to active firmware
    if activate_firmware:
        activate(device_class, version, dst_fs, fw_path=firmware_path)

    # Clean up any temporary files
    firmware_fs.close()
    dst_fs.close()

    # Return install_path
    return install_path


def activate(device_class, version, dst_fs, fw_path=constants.FIRMWARE_PATH):
    """Make a given version active"""
    dst_path = join(device_class, str(version))
    firmware_path = dst_fs.getsyspath(dst_path)
    current_path = os.path.join(fw_path, 'current')
    try:
        # Remove old symlink
        os.remove(current_path)
    except OSError:
        pass
    try:
        os.symlink(firmware_path, current_path)
    except:
        log.exception('unable to link current firmware')


def get_ui(firmware_fs):
    """Get ui (xml) data from firmware"""
    with firmware_fs.open('dataplicity.conf', 'rb') as f:
        conf = settings.read_from_file(f)
    ui_path = conf.get('register', 'ui')
    try:
        return firmware_fs.getcontents(ui_path, 'rb')
    except ResourceNotFoundError:
        return None
