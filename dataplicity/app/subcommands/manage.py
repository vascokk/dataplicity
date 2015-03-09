
from __future__ import unicode_literals
from __future__ import print_function

from dataplicity.app.subcommand import SubCommand
from dataplicity.client import settings
from dataplicity import jsonrpc

import logging
log = logging.getLogger('dataplicity')


class Manage(SubCommand):
    """Launch a browser to manage this device"""
    help = "Launch browser to manage"

    def add_arguments(self, parser):
        parser.add_argument('-u', '--geturl', dest="url_only", action="store_true",
                            help="Get the URL only, don't launch a browser")

    def run(self):
        conf = settings.read(self.app.conf)
        serial = conf.get('device', 'serial')
        device_class = conf.get('device', 'class')
        auth_token = conf.get('device', 'auth')
        server = conf.get('server', 'url')

        remote = jsonrpc.JSONRPC(server)

        with remote.batch() as batch:
            batch.call_with_id('auth_result',
                               'device.check_auth',
                               device_class=device_class,
                               serial=serial,
                               auth_token=auth_token)
            batch.call_with_id('url_result',
                               'device.get_manage_url')

        batch.get_result('auth_result')
        url = batch.get_result('url_result')

        if self.args.url_only:
            print(url)
        else:
            import webbrowser
            webbrowser.open(url)
