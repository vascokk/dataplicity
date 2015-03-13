from __future__ import unicode_literals
from __future__ import print_function

conf_template = """
#----------------------------------------------------------------#
# Dataplicity Device Configuration                               #
# This information is used by the server to identify the device  #
#----------------------------------------------------------------#

[server]
# URL of the Dataplicity JSONRPC server
# Visit this URL for api documentation
url = {SERVER_URL}

[device]
# Name of the device to be displayed in the device tree
name = {name}

# The device class
class = {class}

# A unique serial number
serial = {serial}

# Auth token
auth = {auth_token}

# Text used to identify the device when using --auto
auto_device_text = {auto_device_text}

# Company subdomain or ID when using --auto
subdomain =  {subdomain}

# Directory where dataplicity will store 'live' settings which can be updated by the server
settings = {SETTINGS_PATH}

[daemon]
port = 3366
conf = {FIRMWARE_CONF_PATH}

[firmware]
path = {FIRMWARE_PATH}

"""

rpi_conf_template = """
[extend]
conf = /etc/dataplicity/dataplicity.conf

[server]
push_url = http://sync.dataplicity.com/pushwait

[device]
class = Master RPI
serial = {SERIAL}

[samplers]
path = /tmp/samplers/

[task:proc]
run = dataplicity.tasks.system.ProcessList
poll = 30
data-timeline = process_list

[task:cpu_percent]
run = dataplicity.tasks.system.CPUPercentSampler
poll = 30
data-sampler = cpu_percent

[task:memory_available]
run = dataplicity.tasks.system.AvailableMemorySampler
poll = 30
data-sampler = memory_available

[task:memory_total]
run = dataplicity.tasks.system.TotalMemorySampler
poll = 30
data-sampler = memory_total

[task:disk_available]
run = dataplicity.tasks.system.AvailableDisk
poll = 30
data-sampler = disk_available

[task:disk_total]
run = dataplicity.tasks.system.TotalDisk
poll = 30
data-sampler = disk_total

[task:network]
run = dataplicity.tasks.system.NetworkSampler
poll = 30
data-timeline = network

[task:ifconfig]
run = dataplicity.tasks.system.IfconfigData
poll = 30
data-timeline = ifconfig

[task:sysinfo]
run = dataplicity.tasks.system.SystemInfo
poll = 60
data-timeline = sysinfo

[task:installedpackages]
run = dataplicity.tasks.system.InstalledPackages
poll = 300
data-timeline = installed_packages

[task:setgpio]
run = dataplicity.tasks.rpi.SetGPIO
poll = 30
data-sampler = gpio_sample
data-timeline = gpio_poll

[settings:gpio]
defaults = ./gpio.ini

[task:dashbaord_camera]
run = dataplicity.tasks.rpi.DashControlledCamera
poll = 30
data-timeline = camera

[settings:rpi_camera]
defaults = ./rpi_camera.ini

[timeline:process_list]
[timeline:cpu_percent]
[timeline:network]
[timeline:ifconfig]
[timeline:sysinfo]
[timeline:installed_packages]
[timeline:camera]
[timeline:gpio_poll]

[sampler:memory_available]
[sampler:memory_total]
[sampler:disk_available]
[sampler:disk_total]
[sampler:cpu_percent]
[sampler:gpio_sample]

[m2m]
enabled = yes

[terminal:shell]

"""

linux_conf_template = """
[extend]
conf = /etc/dataplicity/dataplicity.conf

[server]
push_url = http://sync.dataplicity.com/pushwait

[device]
class = Dataplicity Master Linux
serial = {SERIAL}

[samplers]
path = /tmp/samplers/

[task:proc]
run = dataplicity.tasks.system.ProcessList
poll = 30
data-timeline = process_list

[task:cpu_percent]
run = dataplicity.tasks.system.CPUPercentSampler
poll = 30
data-sampler = cpu_percent

[task:memory_available]
run = dataplicity.tasks.system.AvailableMemorySampler
poll = 30
data-sampler = memory_available

[task:memory_total]
run = dataplicity.tasks.system.TotalMemorySampler
poll = 30
data-sampler = memory_total

[task:disk_available]
run = dataplicity.tasks.system.AvailableDisk
poll = 30
data-sampler = disk_available

[task:disk_total]
run = dataplicity.tasks.system.TotalDisk
poll = 30
data-sampler = disk_total

[task:network]
run = dataplicity.tasks.system.NetworkSampler
poll = 30
data-timeline = network

[task:ifconfig]
run = dataplicity.tasks.system.IfconfigData
poll = 30
data-timeline = ifconfig

[task:sysinfo]
run = dataplicity.tasks.system.SystemInfo
poll = 60
data-timeline = sysinfo

[task:installedpackages]
run = dataplicity.tasks.system.InstalledPackages
poll = 300
data-timeline = installed_packages

[timeline:process_list]
[timeline:cpu_percent]
[timeline:network]
[timeline:ifconfig]
[timeline:sysinfo]
[timeline:installed_packages]

[sampler:memory_available]
[sampler:memory_total]
[sampler:disk_available]
[sampler:disk_total]
[sampler:cpu_percent]

[m2m]
enabled = yes

[terminal:shell]

"""

gpio_ini_template = """
[pins]
pin22 = ignore
pin18 = ignore
pin16 = ignore
pin15 = ignore
pin13 = ignore
pin12 = ignore
pin11 = ignore
pin7 = ignore
"""


rpi_camera_template = """
[camera]
frequency = never
last_pic = never
"""