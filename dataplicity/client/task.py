from __future__ import unicode_literals
from __future__ import print_function

from dataplicity import errors
from dataplicity.client import importer
from dataplicity.client.settings import DPConfigParser
from dataplicity.compat import PY2, itervalues

from threading import Thread, Event, RLock, current_thread
from time import time
from collections import defaultdict

if PY2:
    from Queue import Queue, Empty
else:
    from queue import Queue, Empty

import os.path
import sys
import logging
log = logging.getLogger('dataplicity')


def command(f):
    """Mark a callable is a valid task command"""
    f.task_command = True
    return f


def onsignal(signals, sender=None):
    """Makes a method a command that responds to a given signal"""
    if not isinstance(signals, (tuple, list)):
        sigs = (signals,)
    else:
        sigs = signals

    def deco(f):
        f.task_command = True
        f.task_signals = sigs
        f.task_sender = sender
        return f
    return deco


def synchronize(f):
    """Synchronize a method with the task lock"""
    def lock_obj(self, *args, **kwargs):
        self._lock.acquire()
        try:
            return f(self, *args, **kwargs)
        finally:
            self._lock.release()
    return lock_obj


class TaskError(Exception):
    pass


class TaskShuttingDownError(TaskError):
    """The tasklet is shutting down and will not except new commands"""
    pass


class _TaskProxy(object):
    """Provides a little magic for accessing tasks i.e. self.tasks.net rather than self.get_task("net")"""
    def __init__(self, task_manager):
        self.task_manager = task_manager

    def __getattr__(self, name):
        return self.task_manager.get_task(name)

    def __iter__(self):
        return iter(self.task_manager._tasks.values())


class _SignalProxy(object):
    """Provides magic for sending signals

    i.e. this:
    self.signals.power(True)

    rather than:
    self.send_signal("power", True)

    """
    def __init__(self, task_manager):
        self.task_manager = task_manager

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.task_manager.send_signal(name, *args, **kwargs)


class TaskManager(object):
    """A container for tasks that can stop and start groups of tasks"""

    def __init__(self, client):
        self.log = log
        self.client = client
        self._tasks = {}
        self.started = False
        self.tasks = _TaskProxy(self)
        self.signals = _SignalProxy(self)

    @classmethod
    def init_from_conf(cls, client, conf):
        task_manager = TaskManager(client)

        extend_paths = conf.get_list('py', 'path', [])
        extend_paths = [os.path.abspath(os.path.join(os.path.dirname(conf.path), p)) for p in extend_paths]
        for path in extend_paths:
            log.debug('adding {} to Python path'.format(path))
        if extend_paths:
            sys.path = extend_paths + sys.path

        new_tasks = []
        for section, name in conf.qualified_sections('task'):
            if not conf.get_bool(section, 'enabled', True):
                continue
            poll = conf.get(section, 'poll', None)
            if poll is not None:
                poll = float(poll)
            run_py = conf.get(section, 'run', None)
            if run_py is None:
                raise errors.StartupError("[{}]/run not defined".format(section))

            task_class = importer.import_object(run_py)

            # Pull out the data- values from a section
            task_conf = DPConfigParser()
            task_conf.add_section('data')
            for option in conf.options(section):
                if option.startswith('data-'):
                    data_option = option.split('-', 1)[-1]
                    task_conf.set('data', data_option, conf.get(section, option))

            task_instance = task_class(task_manager,
                                       task_conf.get_section('data'),
                                       client,
                                       poll_interval=poll)

            task_manager.add_task(name, task_instance)
            new_tasks.append(task_instance)
            task_manager.log.debug('added task {!r}'.format(task_instance))

        # for task in new_tasks:
        #     task.init()
        return task_manager

    def add_task(self, task_name, task):
        assert not self.started, "Tasks may not be added once the manager is started"
        task.task_manager = self
        task.name = task_name
        self._tasks[task_name] = task
        task.init()

    def get_task(self, task_name):
        return self._tasks[task_name]

    def send_signal(self, name, *args, **kwargs):
        """Send a signal, that may map to one or more commands on a task"""
        self.log.debug("sending signal '{}' with args {!r}, {!r}".format(name, args, kwargs))
        for task in itervalues(self._tasks):
            task._check_signals(name, None, *args, **kwargs)

    def send_signal_from(self, name, sender, *args, **kwargs):
        self.log.debug("sending signal '{}' from {} with args {!r}, {!r}".format(name, "'{}'".format(sender) if sender else None, args, kwargs))
        for task in itervalues(self._tasks):
            task._check_signals(name, sender, *args, **kwargs)

    __getitem__ = get_task

    def __len__(self):
        return len(self._tasks)

    def __iter__(self):
        return iter(self._tasks)

    def start(self):
        """Start all tasks"""
        self.log.debug("starting task manager")
        tasks = self.tasks
        # Run pre_startup first so that on_startup methods are called synchronously
        for task in tasks:
            self.log.debug("initializing task %r" % task)
            try:
                task.pre_startup()
            except Exception as e:
                self.log.exception("exception on pre_startup for task '%s'" % task.name)

        self.client.livesettings.startup(self)
        self.started = True

        # Kick of the threads
        for task in tasks:
            task.start()

    def stop(self):
        """Stops all tasks and blocks till they are finished"""
        self.log.debug("stopping tasks")
        self.signals.stopping()
        if self.started:
            # Notify all the threads we're stopping
            for task in self.tasks:
                task.request_shutdown()
            # Wait for threads to finish
            for task in self.tasks:
                task.join()
                try:
                    task.on_shutdown()
                except Exception as e:
                    self.log.exception("exception on shutdown of task '%s'" % task.name)
        self._tasks.clear()

    def shutdown(self):
        """Informs all tasks to finish gracefully"""
        self.log.debug("graceful shutdown requested")
        for task in tasks:
            task.request_shutdown()


class TaskCommand(object):
    pass


class ShutdownTaskCommand(TaskCommand):
    pass


class Task(Thread):
    """A class to manage threaded self-contained tasks

    Commands are invoked from the command method (or by __call__) and consist of an identifying
    string followed by positional and keyword arguments.

    The command dispatcher translates the name in to a method name that starts
    with cmd_ and invokes that method with the supplied arguments.

    """

    default_poll_interval = 1.0

    def __init__(self, manager, conf, client, poll_interval=None):
        if poll_interval is None:
            poll_interval = self.default_poll_interval
        self._task_manager = manager
        self.conf = conf
        self.client = client
        self._poll_interval = poll_interval
        self._lock = RLock()
        self._q = Queue()
        self._terminate_event = Event()
        super(Task, self).__init__()
        self._start_time = time()
        self.poll_count = 0
        self._signal_map = defaultdict(set)
        self._valid_commands = {}
        self._accept_new_commands = True

        def make_invoker(name):
            def invoke(*args, **kwargs):
                return self.command(name, *args, **kwargs)
            return invoke

        # The magic that makes commands work like regular methods
        for method_name in dir(self):
            if method_name.startswith('_') or method_name[0].isupper():
                continue
            method = getattr(self, method_name)
            if not callable(method):
                continue
            if getattr(method, 'task_command', False):
                setattr(self, method_name, make_invoker(method_name))
                self._valid_commands[method_name] = method
            signals = getattr(method, "task_signals", [])
            signals_sender = getattr(method, 'task_sender', None)
            for sig in signals:
                self._signal_map[sig].add((method.__name__, signals_sender))

    def _check_signals(self, signal, sender, *args, **kwargs):
        if signal in self._signal_map:
            for command_name, command_sender in self._signal_map[signal]:
                if sender is None or command_sender == sender:
                    self.command(command_name, *args, **kwargs)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

    def get_settings(self, name):
        return self.client.livesettings.get(name)

    @property
    def log(self):
        # Get a logger per task
        log = logging.getLogger('dataplicity.task.' + self.name)
        return log

    @property
    def tasks(self):
        if self._task_manager is None:
            return None
        return self._task_manager.tasks

    @property
    def lock(self):
        return self._lock

    @property
    def signals(self):
        return self._task_manager.signals

    def get_task(self, task_name):
        """Invokes a task, possibly in another task thread"""
        assert self._task_manager is not None
        return self._task_manager.get_task(task_name)

    def start(self):
        self._start_time = time()
        super(Task, self).start()

    def init(self):
        """Called after construction to allow task to initialize

        Overriding this method is preferred over __init__

        """
        pass

    def pre_startup(self):
        """Invoked on startup (outside of thread context)"""
        pass

    def on_shutdown(self):
        """Called when the tread is joined in the main thread's context."""
        pass

    def on_startup(self):
        """Invoked in thread context after startup"""
        pass

    def stop(self):
        """Run the queue to completion and exit the thread"""
        # Set the terminate event, so the thread knows to exit
        self._terminate_event.set()
        # Wake up the queue, which may be blocking
        self._q.put(None)

    def request_shutdown(self):
        """Gracefully shutdown"""
        # Tasks may want to override this to ensure they finish
        # what they are doing
        self.log.debug("shutdown requested")
        self.signals.shuttingdown(graceful=True)
        self._q.put(ShutdownTaskCommand())

    @property
    def T(self):
        """Get the time since the task was started"""
        return time() - self._start_time

    def run(self):

        self.log.debug("started")

        # Consume new commands from the queue
        last_poll_time = None

        try:
            self.on_startup()
        except Exception as e:
            self.log.exception("on_startup exception, task will *not* run")
            return

        # Can't do the poll just yet!
        # Must happen after settings change signal

        # try:
        #     self.poll()
        # except Exception:
        #     self.log.exception("error on first poll")

        flushing = False
        while not self._terminate_event.is_set():

            # Condition to break when all pending commands have been processed
            if not self._accept_new_commands and self._q.empty():
                break

            # Pop and execute pending commands off the queue
            # There is a potential edge case here of a task constantly pushing commands,
            # which would cause an infinite loop. Or just starve the poll of cpu time.
            # So we will only process commands for a finite time
            command_loop_start_time = time()
            max_command_loop_time = self._poll_interval / 2.0  # Seems like a sensible compromise
            while time() - command_loop_start_time < max_command_loop_time:
                try:
                    command = self._q.get(timeout=self._poll_interval if not flushing else 0.1)
                except Empty:
                    break
                if isinstance(command, TaskCommand):
                    if isinstance(command, ShutdownTaskCommand):
                        # ShutdownTaskCommand
                        self._accept_new_commands = False
                        flushing = True
                        continue
                # A command packet of None is a null operation used to wake up the queue
                if command is not None:
                    self._on_command(command)

            if not flushing:
                T = time()
                # Inject poll calls at regular intervals
                if last_poll_time is None or T - last_poll_time > self._poll_interval:
                    try:
                        self.poll()
                    except Exception:
                        self.log.exception("error on poll")
                    self.poll_count += 1
                    last_poll_time = T

        self.log.debug("stopped")

    def poll(self):
        """Called at regular intervals"""
        pass

    def command(self, command_name, *args, **kwargs):
        """Issue a command, that maps on to a method + parameters.

        If this method is called from this thread object, the method will be called in the current
        thread context, otherwise it will be posted to the object's thread context

        """
        # Don't allow new commands if we are terminating
        if self._terminate_event.is_set() or not self._accept_new_commands:
            return False

        if command_name not in self._valid_commands:
            raise ValueError("\"{}\" is not a valid command".format(command_name))
        command_packet = (command_name, args, kwargs)

        # If the caller is in the thread context, then we can call the method straight away,
        # without going through the queue
        if current_thread() is self:
            self._on_command(command_packet)
        else:
            #print "Sent to queue %r" % (command_packet,)
            self._q.put(command_packet)
        return True

    __call__ = command

    def post_command(self, command_name, *args, **kwargs):
        """Like `command` but always posts the command to the queue"""
        if self._terminate_event.is_set():
            raise TaskShuttingDownError()
        if command_name not in self._valid_commands:
            raise ValueError("\"{}\" is not a valid command".format(command_name))
        command_packet = (command_name, args, kwargs)
        self._q.put(command_packet)

    def _on_command(self, command):
        """Run the command in the current thread context"""
        command_name, args, kwargs = command
        command_callable = self._valid_commands.get(command_name)
        if command_callable is not None:
            try:
                command_callable(*args, **kwargs)
            except Exception as e:
                self.log.exception("Error on command {}".format(command))


class Poller(Task):
    def __init__(self, poll_callable, poll_interval):
        self.poll_callable = poll_callable
        super(Poller, self).__init__(poll_interval=poll_interval)

    def poll(self):
        self.poll_callable()


class Invoker(Task):
    def __init__(self, invoke_callable):
        self.invoke_callable = invoke_callable
        super(Invoker, self).__init__()

    @command
    def go(self):
        self.invoke_callable()


if __name__ == "__main__":

    class SecondCounter(Task):
        """Counts up in seconds"""

        def pre_startup(self):
            self.count = 0

        def poll(self):
            print(self.count)
            self.count += 1

        @command
        def wait(self):
            from time import sleep
            print("ok, waiting 3 seconds...")
            sleep(3)
            print("done, waiting")

        @onsignal("test")
        def test_signal(self, text):
            print("Got signal: %s" % text)

        @onsignal("test")
        def reverser(self, text):
            print(text[::-1])

    class Capitalizer(Task):

        @onsignal("test")
        def caps(self, text):
            print(text.upper())

        def on_shutdown(self):
            from time import sleep
            print("Shutting down capitalizer")
            sleep(3)
            print("Capitalizer has shut down")

    tasks = TaskManager()
    tasks.add_task("counter", SecondCounter())
    tasks.add_task("caps", Capitalizer())
    tasks.start()
    from dataplicity.compat import raw_input
    try:
        while 1:
            input = raw_input(":-) ")
            if not input:
                tasks.tasks.counter.wait()
            else:
                tasks.signals.test(input)
    finally:
        tasks.stop()
