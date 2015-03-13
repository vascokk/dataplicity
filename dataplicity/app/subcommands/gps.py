from __future__ import unicode_literals
from __future__ import print_function

import logging
from dataplicity.app.subcommand import SubCommand

log = logging.getLogger('dataplicity')


class GPS(SubCommand):
    """ Send an alert """
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--lat', dest="lat", help="latitude. type: float", )
        parser.add_argument('--lng', dest="lng", help="longitude. type: float")

    def run(self):
        args = self.args
        client = self.app.make_client(log)
        remote = client.remote

        lat = args.lat
        lng = args.lng

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            print("lat and lng must be float values")
            return -1

        with remote.batch() as batch:
            batch.call_with_id('auth_result',
                               'device.check_auth',
                               device_class=client.device_class,
                               serial=client.serial,
                               auth_token=client.auth_token)
            batch.call_with_id("add_gps_result",
                               "device.add_gps_coords",
                               lat=lat,
                               lng=lng)
        if not batch.get_result('auth_result'):
            print("Unable to authenticate with the Dataplicity server, check username and password")
            return -1
        if batch.get_result('add_gps_result'):
            print("gps coords sent")
