from dataplicity.client.task import Task, onsignal

import math
from time import time


class WaveMaker(Task):
    """Samples a sin wave"""

    def pre_startup(self):
        """Called prior to running the project"""
        # self.conf contains the data- constants from the conf
        self.sampler = self.conf.get('sampler')

    @onsignal('settings_update', 'waves')
    def on_settings_update(self, name, settings):
        """Catches the 'settings_update' signal for 'wave'"""
        # This signal is sent on startup and whenever settings are changed by the server
        self.amplitude = settings.get_float(self.sampler, 'amplitude', 1.0)
        self.frequency = settings.get_float(self.sampler, 'frequency', 1.0)

    def poll(self):
        """Called on a schedule defined in dataplicity.conf"""
        value = math.sin(time() * self.frequency) * self.amplitude
        self.do_sample(value)

    def do_sample(self, value):
        self.client.sample_now(self.sampler, value)


class AbsWaveMaker(WaveMaker):
    """An alternative wave maker that takes the absolute value of the wave"""

    def do_sample(self, value):
        super(AbsWaveMaker, self).do_sample(abs(value))
