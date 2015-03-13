from __future__ import unicode_literals
from __future__ import print_function

from dataplicity.app.subcommand import SubCommand
from dataplicity.client import settings
from dataplicity import constants
from dataplicity import jsonrpc
from dataplicity import firmware

from fs.zipfs import ZipFS
from fs.osfs import OSFS

import logging
log = logging.getLogger('dataplicity')

import sys
import os
import os.path
from base64 import b64decode
from io import BytesIO


class Deploy(SubCommand):
    help = "Deploy firmware for the Dataplicity daemon"

    def add_arguments(self, parser):
        parser.add_argument(dest="device_class", metavar="Device Class",
                            help="Device class to deploy")
        parser.add_argument('--server', dest="server", metavar="SERVER URL", default=None,
                            help="URL for Dataplicity api")
        parser.add_argument('--name', dest="name", metavar="Device name", default=None,
                            help="Device name")

    def run(self):
        args = self.args
        device_class = args.device_class
        conf_path = constants.CONF_PATH

        if not os.path.exists(conf_path):
            sys.stderr.write('{} does not exist.\n'.format(conf_path))
            sys.stderr.write("please run 'dataplicity init' first\n")
            return -1

        print("reading conf from {}".format(conf_path))
        cfg = settings.read(conf_path)
        serial = cfg.get('device', 'serial')
        auth_token = cfg.get('device', 'auth')
        server_url = cfg.get('server', 'url', constants.SERVER_URL)

        remote = jsonrpc.JSONRPC(server_url)

        print("downloading firmware...")
        with remote.batch() as batch:
            batch.call_with_id('register_result',
                               'device.register',
                               auth_token=auth_token,
                               name=args.name or serial,
                               serial=serial,
                               device_class_name=device_class)
            batch.call_with_id('auth_result',
                               'device.check_auth',
                               device_class=device_class,
                               serial=serial,
                               auth_token=auth_token)
            batch.call_with_id('firmware_result',
                               'device.get_firmware')
        batch.get_result('register_result')
        batch.get_result('auth_result')
        fw = batch.get_result('firmware_result')

        if not fw['firmware']:
            sys.stderr.write('no firmware available!\n')
            return -1
        version = fw['version']

        firmware_bin = b64decode(fw['firmware'])
        firmware_file = BytesIO(firmware_bin)
        firmware_fs = ZipFS(firmware_file)

        dst_fs = OSFS(constants.FIRMWARE_PATH, create=True)

        firmware.install(device_class,
                         version,
                         firmware_fs,
                         dst_fs)

        fw_path = dst_fs.getsyspath('/')
        print("installed firmware {} to {}".format(version, fw_path))

        firmware.activate(device_class, version, dst_fs)
        print("activated {}".format(version))
