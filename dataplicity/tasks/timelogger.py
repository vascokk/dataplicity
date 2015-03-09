from __future__ import unicode_literals
from __future__ import print_function

from dataplicity.client.task import Task

from datetime import datetime


class TimeLogger(Task):
    """Ultra-simple test task that logs the current time"""

    def poll(self):
        self.log.info(datetime.now().ctime())
