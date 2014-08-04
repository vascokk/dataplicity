import json
from random import randint
from time import time
from dataplicity.client.task import Task
import psutil


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


class CPUPercentSampler(Task):
    """Monitor CPU usage percentage"""

    def init(self):
        self.timeline_name = self.conf.get('timeline', 'system.cpu_percent')
        timestamp = int(time() * 1000.0)
        token = str(randint(0, 2 ** 31))
        self.event_id = '{0}_{1}'.format(timestamp, token)

    def poll(self):
        # Get the timeline
        timeline = self.client.get_timeline(self.timeline_name)
        cpu_percent = psutil.cpu_percent(percpu=True)

        event = timeline.new_event(event_type='TEXT',
                                   title='CPU Percent',
                                   text=json.dumps(cpu_percent),
                                   overwrite=True,
                                   hide=True,
                                   event_id=self.event_id)

        event.write()


class TotalMemorySampler(Task):
    """Monitor memory usage - sample in Mb"""

    def init(self):
        self.sampler = self.conf.get('sampler', 'memory_total')

    def poll(self):
        mem = psutil.virtual_memory()
        self.client.sample_now(self.sampler, mem.total / 1024 / 1024)


class AvailableMemorySampler(Task):
    """Monitor memory usage - sample in Mb"""

    def init(self):
        self.sampler = self.conf.get('sampler', 'memory_available')

    def poll(self):
        mem = psutil.virtual_memory()
        self.client.sample_now(self.sampler, mem.available / 1024 / 1024)


class TotalDisk(Task):
    """Monitor disk usage - sample in Gb"""

    def init(self):
        self.sampler = self.conf.get('sampler', 'system.disk_total')

    def poll(self):
        disk = psutil.disk_usage('/')
        self.client.sample_now(self.sampler, disk.total / 1024 / 1024 / 1024)


class AvailableDisk(Task):
    """Monitor disk usage - sample in Gb"""

    def init(self):
        self.sampler = self.conf.get('sampler', 'system.disk_available')

    def poll(self):
        disk = psutil.disk_usage('/')
        self.client.sample_now(self.sampler, disk.free / 1024 / 1024 / 1024)


class ProcessList(Task):
    def init(self):
        self.timeline_name = self.conf.get('timeline', 'process_list')
        timestamp = int(time() * 1000.0)
        token = str(randint(0, 2 ** 31))
        self.event_id = '{0}_{1}'.format(timestamp, token)

    def poll(self):
        # Get the timeline
        timeline = self.client.get_timeline(self.timeline_name)
        process_list = []
        for p in psutil.process_iter():
            data = dict(name=p.name(),
                        username=p.username(),
                        status=p.status())

            try:
                data['memory_percent'] = p.memory_percent()
            except psutil.AccessDenied:
                data['memory_percent'] = 0

            process_list.append(data)

        process_list = sorted(process_list, key=lambda k: k['memory_percent'], reverse=True)

        event = timeline.new_event(event_type='TEXT',
                                   title='Process list',
                                   text=json.dumps(process_list),
                                   overwrite=True,
                                   hide=True,
                                   event_id=self.event_id)

        event.write()


class NetworkSampler(Task):
    """Monitor CPU Network"""

    def init(self):
        self.timeline_name = self.conf.get('timeline', 'system.network')
        timestamp = int(time() * 1000.0)
        token = str(randint(0, 2 ** 31))
        self.event_id = '{0}_{1}'.format(timestamp, token)

    def poll(self):
        # Get the timeline
        timeline = self.client.get_timeline(self.timeline_name)
        network = psutil.net_io_counters(pernic=True)

        event = timeline.new_event(event_type='TEXT',
                                   title='Network stats',
                                   text=json.dumps(network),
                                   overwrite=True,
                                   hide=True,
                                   event_id=self.event_id)

        event.write()