from __future__ import unicode_literals
from __future__ import print_function

from threading import thread
import Queue

import logging
log = logging.getLogger('dataplicity.m2m')


class M2MEvents(thread):

    def __init__(self, exit_event):
        self.exit_event = exit_event
        self.queue = Queue()

    def post_event(self, event):
        self.queue.put(event)

    def run(self):
        while not self.exit_event.is_set():
            try:
                event = self.queue.get(True, 1)
            except Queue.Empty:
                continue
            self.queue.task_done()
            try:
                self.on_event(event)
            except:
                log.exception('error in M2MEvents.on_event')

    def on_event(self, event):
        pass
