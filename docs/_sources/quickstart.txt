Quickstart
==========

The Dataplicity Python module will allow you to create unattended software services to monitor many kinds of sequential data, coupled with a web service to remotely administer and graph the data from the service.

Visit http://www.dataplicity.com for more information


Requirements
~~~~~~~~~~~~

To write a Dataplicity service or run the examples you will need the following.

 * The `dataplicity` module installed in your Python path
 * A computer capable of running Linux

If you installed Dataplicity through Pip, or other official channel, you should now have the ``dataplicity`` command available. Alternatively you can download the source and run `python setup.py install`. Run the following from the command line to confirm you have Dataplicity installed::

    dataplicity --version

The `dataplicity` command is a versatile application that will assist you developing and deploying Dataplicity services.


Running the Samples
~~~~~~~~~~~~~~~~~~~

There are a number of example projects in the Dataplicity source package, which you will find the the ``examples`` directory.


Step 1. Sign Up
+++++++++++++++

To run the samples and develop Dataplicity projects, you will need a Dataplicity account. If you haven't signed up yet, visit https://vendor.dataplicity.com to create an account.


Step 2. Initialize the device
+++++++++++++++++++++++++++++

On a fresh machine you will need to create some default files and authorize with the server. Run the following command to do that (replacing USERNAME and PASSWORD with your Dataplicity login details)::

    dataplicity init -u USERNAME -p PASSWORD

You may need to prepend the above command with ``sudo`` on some systems.


Step 3. Register the device
+++++++++++++++++++++++++++

To run an example project,navigate to your chosen project (it should contain a ``dataplicity.conf`` file) and run the following command::

    dataplicity register


Step 4. Run the project
++++++++++++++++++++++++

You should now have an item in your Dataplicity device tree. Enter the following command to run the project::

    dataplicity run

If you visit your Dataplicity device tree now, you should see a custom UI generated on the fly.



