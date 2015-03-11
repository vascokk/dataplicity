from dataplicity.app.subcommand import SubCommand
from dataplicity import firmware
from dataplicity.client import tools

from fs.opener import fsopendir
from fs.zipfs import ZipFS
from fs.path import dirname, join

import logging
log = logging.getLogger('dataplicity')


def do_build(dataplicity_path):
    """Build firmware in project directory"""
    with fsopendir(dataplicity_path) as src_fs:
        version = firmware.get_version(src_fs)
        print("Building version {:010}...".format(version))
        filename = "firmware-{}.zip".format(version)
        firmware_path = join('__firmware__', filename)
        src_fs.makedir('__firmware__', allow_recreate=True)

        with src_fs.open(firmware_path, 'wb') as zip_file:
            dst_fs = ZipFS(zip_file, 'w')
            firmware.build(src_fs, dst_fs)
            dst_fs.close()

        size = src_fs.getsize(firmware_path)

    print("Wrote {} ({:,} bytes)".format(firmware_path, size))


class Build(SubCommand):
    help = "Build firmware"

    def add_arguments(self, parser):
        pass

    def run(self):

        args = self.args
        #client = self.app.make_client(None)

        conf_path = args.conf or tools.find_conf()
        dataplicity_path = dirname(conf_path)

        do_build(dataplicity_path)
