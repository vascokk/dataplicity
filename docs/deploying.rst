Deploying
=========

Deploying firmware is the process of downloading firmware from the Dataplicity server and installing it on a *device* (typically a linux computer).

To deploy a firmware first initialize the device with the following command::

    dataplicity init -u USERNAME -p PASSWORD

The USERNAME and PASSWORD values should be replaced with your Dataplicity login details. You may need to prefix the init command with ``sudo`` on some systems.

Once the device has been initialized, the following command will download and install the current firmware::

    dataplicity deploy "DEVICE CLASS"

Replacing DEVICE CLASS with the name of the device class (you can find this in the Developer section of the Dataplicity website).

Once deployed, the firmware may be run as a daemon with the following command::

    dataplicity d


Alternative Deploy Method
+++++++++++++++++++++++++

The above method requires a username and password to authorize the device. This may not be ideal if you plan to deploy a large number of devices, as it would require a manual step to be ran on each device or login details to be stored on the device.

Dataplicity supports an alternative method to deploy devices that doesn't require a manual process or login details. Fresh devices register themselves with the server and must be granted permission. They will then download and install the firmware automatically.

To enable the *zero configration* deploy, a dataplicity.conf should be generated with the following command::

    dataplicity init --auto "TEXT TO IDENTIFY DEVICE" --class "DEVICE CLASS" --company SUBDOMAIN

The text for the --auto switch should be a memorable string (to identify the device online). Your company should also be specified with the --company switch, and should be your company *subdomain*.

You can now run the daemon with the following::

    dataplicity d

Without firmware, the daemon will regiser itself with the server. You can grant permission to the device to connect from the Developer menu ('pending devices' tab). Once permission is granted the device will download the firmware and install the next time it syncs with the server.

Note that the contents for `dataplicity.conf` as generate by `dataplicity init` doesn't vary for devices in the same device class. To deploy a large number of devices, you can copy /etc/dataplicity/dataplicity.conf to each device. If you want to generate an appropriate `dataplicity.conf` without installing it you can use the --dry switch and pipe the output to a file.