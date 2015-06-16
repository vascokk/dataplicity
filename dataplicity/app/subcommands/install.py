from __future__ import print_function
from __future__ import unicode_literals

from dataplicity.app.subcommand import SubCommand
from dataplicity import firmware
from dataplicity import constants

from fs.osfs import OSFS
from fs.zipfs import ZipFS

import os
import os.path


class Install(SubCommand):
    """Install firmware"""
    help = "Install firmware"

    def add_arguments(self, parser):
        parser.add_argument(dest="path", metavar="PATH",
                            help="Firmware to install")
        parser.add_argument('-i', dest="install_path", metavar="INSTALL PATH", default=constants.FIRMWARE_PATH,
                            help="Directory where the firmware should be installed")
        parser.add_argument('-a', '--active', dest="make_active", action="store_true",
                            help="make this the active firmware")
        parser.add_argument('-q', '--quiet', dest="quiet", action="store_true",
                            help="silence output")

    def run(self):
        args = self.args

        if args.quiet:
            def out(text):
                pass
        else:
            def out(text):
                print(text)

        firmware_fs = ZipFS(args.path)
        firmware_conf = firmware.get_conf(firmware_fs)
        version = firmware.get_version(firmware_fs)
        device_class = firmware_conf.get('device', 'class')

        out("installing firmware {:010} for device class {}...".format(version, device_class))

        dir_mode = int('775', 8)  # Python 2/3 compatible octal number
        if not os.path.exists(args.install_path):
            try:
                os.makedirs(args.install_path, dir_mode)
            except:
                raise
            else:
                out("created {}".format(args.install_path))

        dst_fs = OSFS(args.install_path, dir_mode=dir_mode)
        install_path = firmware.install(device_class,
                                        version,
                                        firmware_fs,
                                        dst_fs)

        out("installed {} to {}".format(args.path, install_path))

        if args.make_active:
            firmware.activate(device_class,
                              version,
                              dst_fs,
                              fw_path=args.install_path)
