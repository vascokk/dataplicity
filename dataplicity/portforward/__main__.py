"""

A Port Forwarding client for development.

This runs portforwarding outside of the dataplicity daemon, because there are too many processes to keep track of otherwise.

"""

from __future__ import unicode_literals
from __future__ import print_function

from .portforward import PortForwardManager

import logging

FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(format=FORMAT)


M2M_IDENTITY = "055b945e-7f14-11e5-ae34-8344331c88e4"
from dataplicity.client.m2m import M2MClient
m2m = M2MClient("ws://127.0.0.1:90/m2m/", uuid=M2M_IDENTITY)
pf = PortForwardManager(m2m)
pf.add_service('web', 8888, host="127.0.0.1")
pf.run()
