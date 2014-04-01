Dataplicity Command
===================

After installing the dataplicity Python module, you should now be able to run a command line app called `dataplicity`.

The dataplicity command line app can be used to *build*, *publish* and *run* Dataplicity projects, via a number of *subcommands*. Run the following to list the available subcommands::

    dataplicity -h


Subcommands
-----------

To run a subcommand (see below for a list), supply the subcommand name as the first argument to ``dataplicity``. A subcommand may have its own set of switches and options that should appear after the subcommand name on the command line. For example::

    dataplicity manage --geturl

If there is an error running one of the subcommands (and the error message is not helpful) you can get a full Python traceback with the ``--debug`` switch, which should appear before the name of the subcommand. For example, if the ``dataplicity manage`` command produced an error, you would re-run the command with something like the following::

    dataplicity --debug manage --geturl

To get a description of a subcommand and list all available command line switches, run the command with the ``-h`` switch. For example::

    dataplicity manage -h


AUTH
####

This command retrieves an authorization token for the current device. An authorization token is required when syncing with the server. For example::

    dataplicity auth -u USERNAME -p PASSWORD

This command is rarely required because ``dataplicity init`` acquires an authorization token and stores it in ``/etc/datapicity/dataplicity.conf``


BUILD
#####

The build command creates *firmware* for a dataplicity project, and should be run from a dataplicity project directory::

    dataplicity build

The firmware is stored in a directory named ``__firmware__``. The version number is taken from ``firmware.conf``.

D (daemon)
##########

Runs the installed dataplicity project as a daemon. For example::

    dataplicity d

Dataplicity will first read ``/etc/dataplicity/dataplicity.conf`` and run the dataplicity project given in the [daemon] section. Logging will be written to /var/log/syslog

DEPLOY
######

Download and install firmware for a given device class. This requires that ``dataplicity init`` has been run. For example::

    dataplicity deploy "examples.Sine Wave"

EVENT
#####

Insert a event in to a timeline. The following example will create a simple text event::

    dataplicity event mytimeline "Some information about the event" --title="Something happened!"

This example will post a photo event::

    dataplicity event photos "Say Cheese" --title="Remote camera" --image ~/Pictures/photo.jpg

INIT
####

Prepares a machine for running Dataplicity projects by creating the required directories and generating default conf files. This command takes a valid Dataplicity login details and will write an authorization token to `/etc/dataplicity/dataplicity.conf`. For example::

    dataplicity init -u USERNAME -p PASSWORD


INSTALL
#######

Installs a firmware globally. For example::

    dataplicity install __firmware__/firmware6.zip


MANAGE
######

Launches a web browser to manage the current device. For example::

    dataplicity manage


REGISTER
########

Register the current Dataplicity project with the Dataplicity server. This command should be run from a project directory when developing::

    dataplicity register

RUN
###

Runs the local Dataplicity project in the foreground. This command is mainly for development, logs will be written to stdout.


SYNC
####

Sync the running Dataplicity project with the server. This will cause the daemon to immediately sync with the server, outside of the regular sync schedule.
