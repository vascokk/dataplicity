from __future__ import unicode_literals
from __future__ import print_function

import logging
import datetime
from time import mktime
from dataplicity.app.subcommand import SubCommand

log = logging.getLogger('dataplicity')


class Sample(SubCommand):
    """ Send an alert """
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(dest="sampler", help="Sampler name")
        parser.add_argument(dest="value", help="Sampler value")

    def run(self):
        args = self.args
        client = self.app.make_client(log)
        remote = client.remote

        sampler = args.sampler
        value = args.value
        timestamp = mktime(datetime.datetime.utcnow().timetuple())

        with remote.batch() as batch:
            batch.call_with_id('auth_result',
                               'device.check_auth',
                               device_class=client.device_class,
                               serial=client.serial,
                               auth_token=client.auth_token)
            batch.call_with_id("add_sample_result",
                               "device.add_samples",
                               device_class=client.device_class,
                               serial=client.serial,
                               sampler_name=sampler,
                               samples=[[timestamp, value]])
        if not batch.get_result('auth_result'):
            print("Unable to authenticate with the Dataplicity server, check username and password")
            return -1
        if batch.get_result('add_sample_result'):
            print("sample sent")
