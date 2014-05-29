from dataplicity.client.task import Task, onsignal

from contextlib import closing
from urllib import urlopen
import json


class BitstampMonitorTask(Task):
    """Samples a sin wave"""

    @onsignal('settings_update', 'live')
    def on_settings_update(self, name, settings):
        """Catches the 'settings_update' signal for 'wave'"""
        # This signal is sent on startup and whenever settings are changed by the server
        self.ticker_value_name = settings.get('bitstamp', 'sample_value_name', 'last')

    def poll(self):
        """Called on a schedule defined in dataplicity.conf"""
        try:
            with closing(urlopen('https://www.bitstamp.net/api/ticker/')) as f:
                ticker_json = f.read()
            ticker = json.loads(ticker_json)
        except:
            self.log.exception('unable to get ticker information from bitstamp.net')
        else:
            timestamp = float(ticker['timestamp'])
            value = float(ticker[self.ticker_value_name])
            self.log.info('sampled price is {}'.format(value))
            self.client.sample('bitstamp', timestamp, value)
