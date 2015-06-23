from __future__ import print_function
from __future__ import unicode_literals

from dataplicity.app.subcommand import SubCommand

import logging
log = logging.getLogger('dataplicity')


class RegisterSamplers(SubCommand):
    """Register just the samplers for this device with the Dataplicity server"""
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--auth', dest="auth", metavar="AUTH TOKEN", default=None, required=False,
                            help="Authorization token (the default use the auth token in datpalicity.conf)")

    def run(self):
        client = self.app.make_client(log, create_m2m=False)
        remote = client.remote

        samplers = client.samplers.enumerate_samplers()
        if samplers:
            with remote.batch() as batch:
                batch.call_with_id('auth_result',
                                   'device.check_auth',
                                   device_class=client.device_class,
                                   serial=client.serial,
                                   auth_token=client.auth_token)
                batch.call_with_id("create_samplers_result",
                                   "device.create_samplers",
                                   sampler_names=samplers)
            if not batch.get_result('auth_result'):
                print("Unable to authenticate with the Dataplicity server, check username and password")
                return -1
            batch.get_result('create_samplers_result')
