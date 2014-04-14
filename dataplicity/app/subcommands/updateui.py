from dataplicity.app.subcommand import SubCommand
from dataplicity import firmware
from dataplicity.app.errorcodes import ErrorCodes
from dataplicity.jsonrpc import JSONRPCError

from fs.opener import fsopendir
from fs.path import dirname, join

import logging
log = logging.getLogger('dataplicity')


import sys


class UpdateUI(SubCommand):
    """Update UI XML for this firmware"""
    help = "Update UI XML for this firmware"

    def add_arguments(self, parser):
        pass

    def run(self):
        log.setLevel(logging.ERROR)
        args = self.args

        conf_path = self.app.conf
        dataplicity_path = dirname(conf_path)

        client = self.app.make_client(log)
        conf = client.conf
        remote = client.remote
        device_class_name = conf.get('device', 'class')

        with fsopendir(dataplicity_path) as project_fs:
            version = firmware.get_version(project_fs)
            ui = firmware.get_ui(project_fs)

        sys.stdout.write("uploading UI for firmware {:010}...\n".format(version))

        with remote.batch() as batch:
            batch.call_with_id('auth_result',
                               'device.check_auth',
                               device_class=device_class_name,
                               serial=client.serial,
                               auth_token=client.auth_token)
            batch.call_with_id('update_ui_result',
                               'device.update_ui',
                               device_class=device_class_name,
                               version=version,
                               ui=ui)
            batch.call_with_id('url_result',
                               'device.get_manage_url')

        batch.get_result('auth_result')
        try:
            batch.get_result('update_ui_result')
        except JSONRPCError as e:
            if e.code == ErrorCodes.UI_INVALID:
                sys.stderr.write("User Interface definition failed to validate!\n")
                if hasattr(e, 'message'):
                    sys.stderr.write("  {}\n".format(e.message))
                sys.stderr.write('Please check for errors and try again\n')
                return -1
            raise

        url = batch.get_result('url_result')
        sys.stdout.write('UI updated on {}\n'.format(url))

