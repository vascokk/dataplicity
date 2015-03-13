from __future__ import unicode_literals
from __future__ import print_function

from dataplicity.app.subcommand import SubCommand

import logging
log = logging.getLogger('dataplicity')


class MOTD(SubCommand):
    """Get a message of the day"""
    help = "Get a message of the day"

    def run(self):
        client = self.app.make_client(log)
        print(client.remote.call('system.get_motd'))
