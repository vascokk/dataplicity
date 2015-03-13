from __future__ import unicode_literals
from __future__ import print_function

from dataplicity import errors


def import_object(name):
    """Dynamically import an object from a module"""

    module_name, _, object_name = name.rpartition('.')

    try:
        module = __import__(module_name)
    except ImportError as e:
        raise errors.StartupError("Unable to import '{}' ({})".format(name, e))

    for path in module_name.split('.')[1:]:
        module = getattr(module, path, None)

    iobject = getattr(module, object_name, None)
    if iobject is None:
        raise errors.StartupError("Unable to import '{}' from '{}'".format(object_name, module_name))

    return iobject
