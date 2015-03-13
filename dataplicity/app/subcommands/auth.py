from dataplicity.app.subcommand import SubCommand
from dataplicity.client.serial import get_default_serial
from dataplicity.constants import SERVER_URL


class Auth(SubCommand):
    """Get an authorisation token"""
    help = """Get a authorisation token from the server"""

    def add_arguments(self, parser):
        parser.add_argument('--serial', dest="serial", metavar="SERIAL", default=get_default_serial(),
                            help="Serial number for this device, omit to generate a serial number automatically")
        parser.add_argument('-u', '--user', dest="user", metavar="USERNAME", default=None, required=True,
                            help="Your dataplicity.com username")
        parser.add_argument('-p', '--password', dest="password", default=None, required=True,
                            help="Your dataplicity.com password")
        parser.add_argument('--server', dest="server", metavar="SERVER URL", default=SERVER_URL,
                            help="URL for Dataplicity api")

    def run(self):
        args = self.args
        serial = args.serial

        from dataplicity import jsonrpc
        remote = jsonrpc.JSONRPC(args.server)

        auth_token = remote.call('device.auth',
                                 serial=serial,
                                 username=args.user,
                                 password=args.password)
        print(auth_token)
