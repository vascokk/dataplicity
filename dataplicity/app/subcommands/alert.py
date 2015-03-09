import logging
from dataplicity.app.subcommand import SubCommand

log = logging.getLogger('dataplicity')


class Alert(SubCommand):
    """ Send an alert """
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(dest="level", help="alert level", choices=['info', 'warning', 'emergency'])
        parser.add_argument(dest="text", help="Alert text")
        parser.add_argument("-t", "--title", dest="title", default="Alert", required=False, help="Alert title")

    def run(self):
        args = self.args
        client = self.app.make_client(log)
        remote = client.remote

        text = args.text
        title = args.title
        level = args.level

        with remote.batch() as batch:
            batch.call_with_id('auth_result',
                               'device.check_auth',
                               device_class=client.device_class,
                               serial=client.serial,
                               auth_token=client.auth_token)
            batch.call_with_id("add_alert_result",
                               "device.add_alert",
                               title=title,
                               text=text)
        if not batch.get_result('auth_result'):
            print("Unable to authenticate with the Dataplicity server, check username and password")
            return -1
        if batch.get_result('add_alert_result'):
            print("alert sent")


