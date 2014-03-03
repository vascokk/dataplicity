from dataplicity.client.task import Task


class LoadSampler(Task):
    """Monitor system load"""

    def init(self):
        self.sampler = self.conf.get('sampler', 'system.load')

    def poll(self):
        with open('/proc/loadavg', 'rb') as f:
            load_text = f.read()

        try:
            load_1m = float(load_text.split(' ')[0])
        except:
            self.log.exception("Unable to get load avg")
        else:
            self.client.sample_now(self.sampler, load_1m)
