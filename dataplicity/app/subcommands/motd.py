from dataplicity.app.subcommand import SubCommand

import logging
log = logging.getLogger('dataplicity')


class MOTD(SubCommand):
    help = "Register this device"

    def run(self):
        client = self.app.make_client(log)
        client.remote.call('system.get_motd')
