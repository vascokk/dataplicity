from dataplicity.app.subcommand import SubCommand

import sys
import logging
log = logging.getLogger('dataplicity')


class Event(SubCommand):
    """Add an event to a timeline"""
    help = """Add an event to a timeline"""

    def add_arguments(self, parser):
        parser.add_argument(dest="timeline",
                            help="Name of the timeline")
        parser.add_argument(dest="text",
                            help="Event text")
        parser.add_argument('-t', '--title', dest="title", required=False, default="event from the command line",
                            help="Title of the event")
        parser.add_argument('-i', '--image', dest="image", required=False, default=None,
                            help="Path to image")

    def run(self):
        args = self.args
        client = self.app.make_client(log)
        timeline = client.timelines.get_timeline(args.timeline)

        if args.image:
            try:
                with timeline.new_event('IMAGE', text=args.text, title=args.title) as event:
                    event.attach_file(args.image, name="photo")
            except IOError:
                sys.stderr.write('image file not found')
        else:
            with timeline.new_event('TEXT', text=args.text, title=args.title):
                pass
