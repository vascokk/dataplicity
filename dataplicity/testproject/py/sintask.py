from dataplicity.client import Task

import math


class SinWaveTask(Task):
    """Create a sin wave sample"""

    def init(self):
        # Called immediately after the Task is created
        # Set up any variables from self.conf which contains the data section
        conf = self.conf
        self.sampler = conf.get('sampler')
        self.height = conf.get_float('height', 1000.0)
        self.frequency = conf.get_float('frequency', 20.0)

    def get_sample(self):
        sample = math.sin(self.T * math.PI * self.frequency) * self.height
        return sample

    # Called at regular intervals
    def poll(self):
        sample = self.get_sample()
        self.log("got sample {}".formaT(sample))
        self.client.sample(self.sampler, sample)


class AbsSinWaveTask(SinWave):

    def get_sample(self):
        sample = super(AbsSinWaveTask, self).get_sample()
        return abs(sample)