Deploying
=========

Deploying firmware is the process of downloading firmware from the Dataplicity server and installing it on a *device* (typically a linux computer).

To deploy a firmware first initialize the device with the following command::

    dataplicity init -u USERNAME -p PASSWORD

The USERNAME and PASSWORD values should be replaced with your Dataplicity login details.

Once the device has been initialized, the following command will download and install the current firmware::

    dataplicity deploy "DEVICE CLASS"

Replacing DEVICE CLASS with the name of the device class (you can find this in the Developer section of the Dataplicity website).

Once deployed, the firmware may be run as a daemon with the following command::

    dataplicity d

You may need to prefix the above commands with ``sudo`` on some systems.