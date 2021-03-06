from dataplicity.app.subcommands.daemon import Daemon
from dataplicity.app.subcommand import SubCommand


class Run(SubCommand):
    """Run the dataplicity service in the foreground"""
    help = """Run a dataplicity service in the foreground (useful for debugging)"""

    def add_arguments(self, parser):
        parser.add_argument('--no-update', dest="noupdate", action="store_true", default=False,
                            help="disable auto update")
        parser.add_argument('--no-sync', dest="nosync", action="store_true", default=False,
                            help="do not sync (for debugging purposes)")
        return parser

    def make_daemon(self, debug=True):
        args = self.args
        if debug is None:
            debug = args.debug
        self.app.init_logging()
        dataplicity_daemon = Daemon(self.app.conf,
                                    foreground=True,
                                    debug=debug,
                                    auto_update=not args.noupdate,
                                    no_sync=args.nosync,
                                    rpc_url=args.server_url)
        return dataplicity_daemon

    def run(self):
        dataplicity_daemon = self.make_daemon()
        #dataplicity_daemon.sync_now()
        dataplicity_daemon.start()
