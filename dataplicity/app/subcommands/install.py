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

    def run(self):
        args = self.args

        firmware_fs = ZipFS(args.path)
        firmware_conf = firmware.get_conf(firmware_fs)
        version = firmware.get_version(firmware_fs)
        device_class = firmware_conf.get('device', 'class')

        print "installing firmware {:010} for device class {}...".format(version, device_class)

        if not os.path.exists(args.install_path):
            try:
                os.makedirs(args.install_path)
            except:
                raise
            else:
                print "created {}".format(args.install_path)

        dst_fs = OSFS(args.install_path)
        install_path = firmware.install(device_class,
                                        version,
                                        firmware_fs,
                                        dst_fs)

        print "installed {} to {}".format(args.path, install_path)
