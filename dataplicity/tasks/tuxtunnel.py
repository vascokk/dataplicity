import shlex
from dataplicity.client.task import Task
from dataplicity import jsonrpc
import json
from subprocess import Popen, PIPE
import psutil


class DeviceMetaInfo(Task):
    def init(self):
        self.rpc_url = self.conf.get('rpcurl', 'http://tuxtunnel.com/jsonrpc')
        self.remote = jsonrpc.JSONRPC(self.rpc_url)

    def get_data(self):
        # determine if B plus model
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

        # get cpu speed
        with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as fp:
            try:
                mhz = int(fp.read())/1000
            except ValueError:
                mhz = None

        # get total memory
        total_memory = psutil.virtual_memory().total/1024/1024

        # uname
        p1 = Popen(['uname', '-a'], stdout=PIPE, stderr=PIPE)
        stdout, stderr = p1.communicate()
        if not stderr:
            uname = stdout
        else:
            uname = None

        data = dict(serial=self.client.serial,
                    b_plus=b_plus,
                    mhz=mhz,
                    total_memory=total_memory,
                    uname=uname)

        return data


    def on_startup(self):
        timeline = self.client.get_timeline(self.timeline_name)
        data = self.get_data()

        self.remote.call('device_meta_data',
                         **data)

