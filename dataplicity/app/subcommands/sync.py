from dataplicity.app.subcommand import SubCommand
from dataplicity.app import comms

import sys


class Sync(SubCommand):
    """Sync with server"""
    help = """Sync with server"""

    def run(self):
        result = comms.Comms().sync()
        if result != "OK":
            sys.stderr.write("Sync failed! ({})\n".format(result or 'internal error'))
            return -1
        else:
            return 0
