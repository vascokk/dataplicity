from __future__ import unicode_literals
from __future__ import print_function

"""
Creates a database of timestamped events.

"""

from dataplicity import constants
from dataplicity.compat import text_type, itervalues

import os.path
from os.path import splitext
from time import time
from random import randint
from json import dumps, loads
from operator import itemgetter
from base64 import b64encode
from os.path import basename

from fs.osfs import OSFS
from fs.errors import FSError

import logging
log = logging.getLogger('dataplicity')

# maps event types to an event class
_event_registry = {}


def register_event(event_type):
    """Class decorator to register a new event class"""
    def class_deco(cls):
        cls.event_type = event_type
        _event_registry[event_type] = cls
        return cls
    return class_deco


class TimelineError(Exception):
    pass


class UnknownTimelineError(TimelineError):
    pass


class UnknownEventError(TimelineError):
    pass


class TimelineFullError(TimelineError):
    pass


class Event(object):
    """base class for events"""

    def __init__(self, timeline, event_id, timestamp, *args, **kwargs):
        self.timeline = timeline
        self.event_id = event_id
        self.timestamp = timestamp
        self.attachments = []
        self.data = {}
        self.init(*args, **kwargs)
        super(Event, self).__init__()

    def init(self, title='untitled', text='', text_format="TEXT", **kwargs):
        self.title = title
        self.text = text
        self.text_format = text_format
        self.hide = kwargs.get('hide', False)
        self.overwrite = kwargs.get('overwrite', False)

    def to_data(self):
        """Get a JSON serializable structyre for this event"""
        return {"timestamp": self.timestamp,
                "event_type": self.event_type,
                "title": self.title,
                "text": self.text,
                "text_format": self.text_format,
                "data": self.data.copy(),
                "attachments": self.attachments,
                "hide": self.hide,
                "overwrite": self.overwrite}

    def __repr__(self):
        return "<event {}>".format(self.event_id)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.write()

    def attach_file(self, filename, name=None, ext=None):
        """Attach a file to this event"""
        if name is None:
            name = filename
        with open(filename, 'rb') as f:
            data_bin = f.read()
        return self.attach_bytes(data_bin, filename=filename, name=name)

    def attach_bytes(self, data_bin, filename=None, name=None, ext=None):
        """Attach binary data to this event"""
        if ext is None and filename is not None:
            ext = splitext(filename)[-1]
        data_b64 = b64encode(data_bin)
        if filename is not None:
            filename_base = basename(filename)
        else:
            filename_base = None
        attachment = {
            "data": data_b64,
            "encoding": 'base64',
            "name": name or filename_base,
            "filename": filename_base,
            "ext": ext
        }
        self.attachments.append(attachment)
        return self

    def write(self):
        """Write the event (called automatically)"""
        self.timeline._write_event(self.event_id, self)
        return self


@register_event("TEXT")
class TextEvent(Event):
    """A simple text event"""
    pass


@register_event('IMAGE')
class ImageEvent(Event):
    """An event with an image"""

    def init(self, title='untitled', text='', text_format='TEXT', filename='', name='', ext=''):
        self.title = title
        self.text = text
        self.text_format = text_format
        self.filename = filename
        self.name = name
        self.ext = ext

    def to_data(self):
        return {"timestamp": self.timestamp,
                "event_type": self.event_type,
                "title": self.title,
                "text": self.text,
                "text_format": self.text_format,
                "filename": self.filename,
                "name": self.name,
                "ext": self.ext,
                "data": self.data,
                "attachments": self.attachments}


class TimelineManager(object):
    """Manages a collection of timelines"""

    def __init__(self, path):
        self.path = path
        self.timelines = {}

    def __nonzero__(self):
        return bool(self.timelines)

    def __iter__(self):
        return itervalues(self.timelines)

    @classmethod
    def init_from_conf(cls, client, conf):
        timelines_path = conf.get('timelines', 'path', constants.TIMELINE_PATH)
        timelines_path = os.path.join(timelines_path, client.device_class)
        timeline_manager = cls(timelines_path)

        for section, name in conf.qualified_sections('timeline'):
            max_events = conf.get(section, 'max_events', None)
            timeline_manager.new_timeline(name, max_events=max_events)
        return timeline_manager

    def new_timeline(self, name, max_events=None):
        """Create a new timeline and store it"""
        path = os.path.join(self.path, name)
        timeline = Timeline(path, name, max_events=max_events)
        self.timelines[timeline.name] = timeline

    def get_timeline(self, timeline_name):
        try:
            timeline = self.timelines[timeline_name]
        except KeyError:
            raise UnknownTimelineError("No timeline called '{}' exists".format(timeline_name))
        else:
            return timeline


class Timeline(object):
    """A timeline is a sequence of timestamped events."""

    def __init__(self, path, name, max_events=None):
        self.path = path
        self.name = name
        self.fs = OSFS(path, create=True)
        self.max_events = max_events

    def __repr__(self):
        return "Timeline({!r}, {!r}, max_events={!r})".format(self.path, self.name, self.max_events)

    def new_event(self, event_type, timestamp=None, *args, **kwargs):
        """Create and return an event, to be used as a context manager"""
        if self.max_events is not None:
            size = len(self.fs.listdir(wildcard="*.json"))
            if size >= self.max_events:
                raise TimelineFullError("The timeline has reached its maximum size")

        if timestamp is None:
            timestamp = int(time() * 1000.0)
        try:
            event_cls = _event_registry[event_type]
        except KeyError:
            raise UnknownEventError("No event type '{}'".format(event_type))

        # Make an event id that we can be confident it's unique
        token = str(randint(0, 2 ** 31))
        event_id = kwargs.pop('event_id', None) or "{}_{}_{}".format(event_type, timestamp, token)
        event = event_cls(self, event_id, timestamp, *args, **kwargs)
        log.debug('new event {!r}'.format(event))
        return event

    def new_photo(self, file, filename=None, ext=None, **kwargs):
        """Create a new photo object"""
        event = self.new_event('IMAGE', **kwargs)

        if hasattr(file, 'getvalue'):
            bytes = file.getvalue()
        elif file is not None:
            if isinstance(file, text_type):
                with open(file, 'rb') as f:
                    bytes = f.read()
            else:
                bytes = file.read()
        else:
            if bytes is None:
                raise ValueError("A value for 'file' or 'bytes' is required")
        event.attach_bytes(bytes, name='photo', filename=filename, ext=ext)
        return event

    def get_events(self, sort=True):
        """Get all accumulated events"""
        events = []
        for event_filename in self.fs.listdir(wildcard="*.json"):
            with self.fs.open(event_filename, 'rb') as f:
                event = loads(f.read().decode('utf-8'))
                events.append(event)
        if sort:
            # sort by timestamp
            events.sort(key=itemgetter('timestamp'))
        return events

    def clear_all(self):
        """Clear all stored events"""
        for filename in self.fs.listdir(wildcard="*.json"):
            try:
                self.fs.remove(filename)
            except FSError:
                pass

    def clear_events(self, event_ids):
        """Clear any events that have been processed"""
        for event_id in event_ids:
            filename = "{}.json".format(event_id)
            try:
                self.fs.remove(filename)
            except FSError:
                pass

    def _write_event(self, event_id, event):
        if hasattr(event, 'to_data'):
            event = event.to_data()
        event['event_id'] = event_id
        event_json = dumps(event, indent=4).encode('utf-8')
        filename = "{}.json".format(event_id)
        with self.fs.open(filename, 'wb') as f:
            f.write(event_json)


if __name__ == "__main__":

    timelines = TimelineManager('/tmp/timeline')
    timelines.new_timeline('test')

    timeline = timelines.get_timeline('test')
    print(timeline)
    timeline.add_event('TEXT', text="Hello, World!", title="Greeting")

    with timeline.new_event('TEXT', text="Frodo", title="Hobbits") as event:
        event.attach('frodo.jpg', name="photo")

    events = timeline.get_events()
    from pprint import pprint
    pprint(events)
