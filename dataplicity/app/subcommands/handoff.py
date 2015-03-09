from __future__ import unicode_literals
from __future__ import print_function


import logging
from dataplicity.app.subcommand import SubCommand

log = logging.getLogger('dataplicity')

conf_template = """
[extend]
conf = /etc/dataplicity/dataplicity.conf

[device]
class = Raspberry Pi
serial = {SERIAL}

[samplers]
path = /tmp/samplers/

[task:proc]
run = dataplicity.tasks.system.ProcessList
poll = 5
data-timeline = process_list

[task:cpu_percent]
run = dataplicity.tasks.system.CPUPercentSampler
poll = 5
data-timeline = cpu_percent

[task:memory_available]
run = dataplicity.tasks.system.AvailableMemorySampler
poll = 5
data-sampler = memory_available

[task:memory_total]
run = dataplicity.tasks.system.TotalMemorySampler
poll = 5
data-sampler = memory_total

[task:disk_available]
run = dataplicity.tasks.system.AvailableDisk
poll = 5
data-sampler = disk_available

[task:disk_total]
run = dataplicity.tasks.system.TotalDisk
poll = 5
data-sampler = disk_total

[task:network]
run = dataplicity.tasks.system.NetworkSampler
poll = 5
data-timeline = network

[timeline:process_list]
[timeline:cpu_percent]
[timeline:network]

[sampler:memory_available]
[sampler:memory_total]
[sampler:disk_available]
[sampler:disk_total]
"""


class Handoff(SubCommand):
    help = "handoff rpi device"

    def add_arguments(self, parser):
        parser.add_argument('--usercode', dest="usercode", action="store",
                            help="base64 encoded usercode")

    def run(self):
        args = self.args
        usercode = args.usercode

        client = self.app.make_client(log, conf='/etc/dataplicity/dataplicity.conf', create_m2m=False)
        remote = client.remote
        conf = client.conf

        device_class_name = conf.get('device', 'class')

        # determine if B+ model
        b_plus = None
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BOARD)
            try:
                GPIO.setup(29, GPIO.OUT)
            except ValueError:
                b_plus = False
            else:
                b_plus = True
        except ImportError:
            pass

        with remote.batch() as batch:
            batch.call_with_id('handoff',
                               'device.handoff',
                               usercode=usercode,
                               auth_token=client.auth_token,
                               rpi_b_plus=b_plus)

        handoff_result = batch.get_result('handoff')

        if handoff_result:
            print('Device registered successfully')
        else:
            print('There was a problem registering your device')
