from __future__ import absolute_import

from dataplicity.app.subcommand import SubCommand
from dataplicity.client import Client
from dataplicity import constants
from dataplicity.client import settings

from daemon import DaemonContext

import sys
import os
import time
import socket
from threading import Thread, Event
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

        client = self.client = Client(conf_path, log=self.log)
        conf = client.conf

        self.poll_rate_seconds = conf.get_float("daemon", "poll", 60.0)
        self.last_check_time = None
        self.pid_path = abspath(conf.get('daemon', 'pidfile', '/var/run/dataplicity.pid'))

        self.server_closing_event = Event()
        #self.comms = comms.Comms()

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
        return
        client.connect_wait(event=event, sync_func=sync_func)

    def exit(self, command=None):
        """Exit daemon now, and run optional command"""
        self.exit_command = command
        self.exit_event.set()

    def start(self):

        self.log.debug('starting dataplicity service with conf {}'.format(self.conf_path))

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.client.sync()
        except:
            self.log.exception("sync failed")
        self.client.tasks.start()
        self.log.debug('ready')
        sync_push_thread = Thread(target=self._push_wait,
                                  args=(self.client,
                                        self.server_closing_event,
                                        lambda: None))
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
                server_socket.bind(('', 8888))
                server_socket.settimeout(self.poll_rate_seconds)
                server_socket.listen(5)
            except:
                self.log.exception('unable to start dataplicity daemon')
                return -1

            try:
                while not self.exit_event.isSet():
                    try:
                        client, _address = server_socket.accept()
                    except socket.timeout:
                        pass
                    else:
                        self.handle_client_command(client)
                        continue

                    t = time.time()
                    try:
                        self.poll(t)
                        time.sleep(0.25)
                    except Exception as e:
                        self.log.debug('error in poll')

            except SystemExit:
                self.log.debug("exit requested")
                return

            except KeyboardInterrupt:
                self.log.debug("user Exit")
                return

        except Exception as e:
            self.log.exception()

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
            sync_push_thread.join(2)
            self.log.debug("goodbye")

            if self.exit_event.isSet() and self.exit_command is not None:
                time.sleep(1)  # Maybe redundant
                self.log.debug("Executing %s" % self.exit_command)
                os.system(self.exit_command)

    def poll(self, t):
        try:
            self.client.sync()
        except Exception:
            self.log.exception('poll failed')

    def handle_client_command(self, client):
        """Read lines sent by client"""
        client.setblocking(False)
        buf = ''
        try:
            try:
                while 1:
                    c = client.recv(4096)
                    if not c:
                        break
                    buf += c
                    while '\n' in buf:
                        line, buf = c.split('\n', 1)
                        reply = self.on_client_command(line)
                        if reply is not None:
                            client.sendall(reply.rstrip('\n') + '\n')
            except socket.error:
                pass

        finally:
            if client is not None:
                client.shutdown(socket.SHUT_RDWR)
                client.close()

    def on_client_command(self, command):
        if command == "SYNC":
            self.log("SYNC client command")
            self.manager.sync()
        elif command == "STATUS":
            self.log("STATUS client command")
            return "running"
        elif command == "SHUTDOWN":
            self.log("SHUTDOWN client command")
            self.client.tasks.request_shutdown()
        elif command == "RESTART":
            self.exit(' '.join(sys.argv))


class FlushFile(file):
    def write(self, data):
        ret = super(FlushFile, self).write(data)
        self.flush()
        return ret


class D(SubCommand):
    """Run a Dataplicity daemon process"""
    help = """Run the Dataplicity daemon"""

    def add_arguments(self, parser):
        parser.add_argument('-f', '--foreground', dest='foreground', action="store_true", default=False,
                            help="Run daemon in foreground")
        parser.add_argument('-k', '--kill', dest="kill", action="store_true", default=False,
                            help="Kill currently running daemon")
        parser.add_argument('-r', '--restart', dest='restart', action="store_true",
                            help="restart running server")

    def make_daemon(self, debug=None):
        conf_path = self.args.conf or constants.CONF_PATH
        conf_path = abspath(conf_path)

        conf = settings.read(conf_path)
        conf_path = conf.get('daemon', 'conf', conf_path)

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
            dataplicity_daemon = self.make_daemon(debug=False)
            dataplicity_daemon.comms('RESTART')
            return 0

        if args.kill:
            dataplicity_daemon = self.make_daemon(debug=False)
            pid = dataplicity_daemon.get_pid()
            if pid is not None:
                os.system("kill %s" % pid)
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
