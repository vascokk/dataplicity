from __future__ import absolute_import

from dataplicity.app.subcommand import SubCommand
from dataplicity.app import comms
from dataplicity.client import Client
from dataplicity.client.exceptions import ForceRestart, ClientException
from dataplicity import constants
from dataplicity.client import settings

from daemon import DaemonContext

import sys
import os
import time
import socket
from threading import Event, Thread
from os.path import abspath
import logging


class Daemon(object):
    """Dataplicity device management process"""

    def __init__(self,
                 conf_path=None,
                 foreground=False,
                 debug=False):
        self.conf_path = conf_path
        self.foreground = foreground
        self.debug = debug

        self.log = logging.getLogger('dataplicity')

        client = self.client = Client(conf_path,
                                      check_firmware=not foreground,
                                      log=self.log)
        conf = client.conf

        self.poll_rate_seconds = conf.get_float("daemon", "poll", 60.0)
        self.last_check_time = None
        self.pid_path = abspath(conf.get('daemon', 'pidfile', '/var/run/dataplicity.pid'))

        self.server_closing_event = Event()

        # Command to execute with the daemon exits
        self.exit_command = None
        self.exit_event = Event()

    def get_pid(self):
        try:
            with open(self.pid_path, 'r') as fpid:
                return fpid.read()
        except IOError:
            return None

    def _push_wait(self, client, event, sync_func):
        client.connect_wait(event, sync_func)

    def exit(self, command=None):
        """Exit daemon now, and run optional command"""
        self.exit_command = command
        self.exit_event.set()

    def start(self):

        self.log.debug('starting dataplicity service with conf {}'.format(self.conf_path))

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.client.tasks.start()
        self.log.debug('ready')
        sync_push_thread = Thread(target=self._push_wait,
                                  args=(self.client,
                                        self.server_closing_event,
                                        self.sync_now))
        sync_push_thread.daemon = True
        try:
            if not self.foreground:
                pid = str(os.getpid())
                try:
                    with open(self.pid_path, 'wb') as pid_file:
                        pid_file.write(pid)
                except Exception as e:
                    self.log.exception("Unable to write pid file (%s)", e)
                    raise

            sync_push_thread.start()
            try:
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.bind(('127.0.0.1', 8888))
                server_socket.settimeout(self.poll_rate_seconds)
                server_socket.listen(5)
            except:
                self.log.exception('unable to start dataplicity daemon')
                return -1

            try:
                while not self.exit_event.isSet():
                    try:
                        self.poll(time.time())
                    except ClientException:
                        raise
                    except Exception as e:
                        self.log.exception('error in poll')

                    try:
                        client, _address = server_socket.accept()
                    except socket.timeout:
                        pass
                    else:
                        self.handle_client_command(client)
                        continue

            except SystemExit:
                self.log.debug("exit requested")
                return

            except KeyboardInterrupt:
                self.log.debug("user Exit")
                return

        except ForceRestart:
            self.log.info('restarting...')
            self.exit(' '.join(sys.argv))

        except Exception as e:
            self.log.exception('error in daemon main loop')

        finally:
            try:
                #server_socket.shutdown(socket.SHUT_RDWR)
                server_socket.close()
                del server_socket
            except Exception as e:
                self.log.exception(e)

            self.log.debug("closing")
            self.server_closing_event.set()
            self.client.tasks.stop()
            self.log.debug("goodbye")

            if self.exit_event.is_set() and self.exit_command is not None:
                time.sleep(1)  # Maybe redundant
                self.log.debug("Executing %s" % self.exit_command)
                os.system(self.exit_command)

    def poll(self, t):
        self.sync_now(t)

    def sync_now(self, t=None):
        if t is None:
            t = time.time()
        try:
            self.client.sync()
        except ClientException:
            raise
        except Exception:
            self.log.exception('sync failed')

    def handle_client_command(self, client):
        """Read lines sent by client"""
        #client.setblocking(False)
        try:
            try:
                command = client.recv(128).rstrip('\n')
                if command:
                    reply = self.on_client_command(command)
                if reply is not None:
                    client.sendall(reply.rstrip('\n') + '\n')
            except socket.error:
                pass

        finally:
            if client is not None:
                client.shutdown(socket.SHUT_RDWR)
                client.close()

    def on_client_command(self, command):
        if command == 'RESTART':
            self.log.info('restart requested')
            self.exit(' '.join(sys.argv))
            return "OK"

        elif command == 'STOP':
            self.log.info('stop requested')
            self.exit()
            return "OK"

        elif command == "SYNC":
            self.log.info('sync requested')
            try:
                self.sync_now()
            except Exception as e:
                return str(e)
            else:
                return "OK"

        elif command == "STATUS":
            self.log.info('status requested')
            return "running"

        return "BADCOMMAND"


# class FlushFile(file):
#     def write(self, data):
#         ret = super(FlushFile, self).write(data)
#         self.flush()
#         return ret


class D(SubCommand):
    """Run a Dataplicity daemon process"""
    help = """Run the Dataplicity daemon"""

    @property
    def comms(self):
        return comms.Comms()

    def add_arguments(self, parser):
        parser.add_argument('-f', '--foreground', dest='foreground', action="store_true", default=False,
                            help="run daemon in foreground")
        parser.add_argument('-s', '--stop', dest="stop", action="store_true", default=False,
                            help="stop the daemon")
        parser.add_argument('-r', '--restart', dest='restart', action="store_true",
                            help="restart running daemon")
        parser.add_argument('-t', '--status', dest="status", action="store_true",
                            help="status of the daemon")
        parser.add_argument('-y', '--sync', dest="sync", action="store_true", default=False,
                            help="sync now")

    def make_daemon(self, debug=None):
        conf_path = self.args.conf or constants.CONF_PATH
        conf_path = abspath(conf_path)

        conf = settings.read(conf_path)
        firmware_conf_path = conf.get('daemon', 'conf', conf_path)
        # It may not exist if there is no installed firmware
        if os.path.exists(firmware_conf_path):
            conf_path = firmware_conf_path

        if debug is None:
            debug = self.args.debug or self.args.foreground

        self.app.init_logging(self.app.args.logging,
                              foreground=self.args.foreground)
        dataplicity_daemon = Daemon(conf_path,
                                    foreground=self.args.foreground,
                                    debug=debug)
        return dataplicity_daemon

    def run(self):
        args = self.args

        if args.restart:
            self.comms.restart()
            return 0

        if args.stop:
            self.comms.stop()
            return 0

        if args.sync:
            self.comms.sync()
            return 0

        if args.status:
            running, msg = self.comms.status()
            if not running:
                sys.stdout.write('not running\n')
            else:
                sys.stdout.write(msg + '\n')
            return 0

        try:
            if args.foreground:
                dataplicity_daemon = self.make_daemon()
                dataplicity_daemon.start()
            else:
                daemon_context = DaemonContext()
                with daemon_context:
                    dataplicity_daemon = self.make_daemon()
                    dataplicity_daemon.start()

        except Exception, e:
            from traceback import print_exc
            print_exc(e)
