Developing Dataplicity Projects
===============================

Developing a Dataplicity Project is an iterative cycle of making changes and testing. When you are happy with a given version it can be **published** to the Dataplicity server. This will make the update available to all devices with the same device class.

A firmware consists of a snapshot of the project directory, minus any irrelevant files (temporary files, source control files and derived files etc).

The current firmware version is stored in an INI file called ``firmware.conf``, which should be in the same directory as ``dataplicity.conf``. The following is an example of a typical ``firmware.conf`` file::

    [firmware]
    version = 9
    exclude = *.pyc
        __*__
        .*
        .hg
        .git

The one and only section, [firmware], contains the current version of the firmware and a list of wildcard paths to exclude from the project directory when it is published.


Building & Publishing
~~~~~~~~~~~~~~~~~~~~~

To build the current firmware, run ``dataplicity build`` from the project directory. This will zip up files in the project directory, with the exception of any paths matching an exclude wildcard, and store the resulting firmware in a directory called `__firmware__`.

To publish a firmware (upload it to the server), use `dataplicity publish`.

Build and publish can also be combined in to a single step with the ``--build`` switch on publish. For example::

    dataplicity publish --build