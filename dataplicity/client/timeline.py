"""
Creates a database of timestamp events.

"""


from time import time
from random import randint
from json import dumps, loads
from operator import itemgetter

from fs.osfs import OSFS
from fs.errors import FSError

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


class UnknownEventError(Exception):
	pass


class TimelineFullError(Exception):
	pass


class Event(object):
	"""base class for events"""
	def __init__(self, event_id, timestamp, *args, **kwargs):
		self.event_id = event_id
		self.timestamp = timestamp
		self.init(*args, **kwargs)

	def serialize(self):
		raise NotImplementedError


@register_event("TEXT")
class TextEvent(Event):

	def init(self, title, text, text_format="TEXT"):
		self.title = title
		self.text = text
		self.text_format = text_format

	def serialize(self):
		return {"timestamp": self.timestamp,
				"event_type": self.event_type,
				"text": self.text,
				"text_format": self.text_format}


class TimeLine(object):

	def __init__(self, name, path, max_events=None):
		self.name = name
		self.fs = OSFS(path, create=True)
		self.max_events = max_events

	@classmethod
	def init_from_conf(cls, client, conf):
		timeline_path = conf.get('timeline', path, constants.TIMELINE_PATH)
		max_events = conf.get('timeline', 'max_events', None)
		return TimeLine(timeline_path, max_events=None)

	def add_event(self, event_type, timestamp=None, *args, **kwargs):
		"""Add a new event of a given type to the timeline"""
		if self.max_events is not None:
			size = len(self.fs.listdir(wildcard="*.json"))
			if size >= self.max_events:
				raise TimelineFullError("The timelines has reached its maximum size")

		if timestamp is None:
			timestamp = int(time() * 1000.0)
		try:
			event_cls = _event_registry[event_type]
		except KeyError:
			raise UnknownEventError("No event type '{}'".format(event_type))

		# Make an event id that we can be confident is unique
		token = str(randint(0, 2**31))
		event_id = "{}_{}_{}".format(event_type, timestamp, token)
		event = event_cls(event_id, timestamp, *args, **kwargs)
		self._write_event(event_id, event)

	def get_events(self, sort=True):
		"""Get all accumulated events"""
		events = []
		for event_filename in self.fs.listdir(wildcard="*.json"):
			with self.fs.open(event_filename, 'rb') as f:
				event = loads(f.read())
				events.append(event)
		if sort:
			events.sort(key=itemgetter('timestamp'))
		return events

	def clear_events(self, event_ids):
		"""Clear any events that have been processed"""
		for event_id in event_ids:
			filename = "{}.json".format(event_id)
			try:
				self.fs.remove(filename)
			except FSError:
				pass

	def _write_event(self, event_id, event):
		if hasattr(event, 'serialize'):
			event = event.serialize()
		event['_id'] = event_id
		event_json = dumps(event)
		filename = "{}.json".format(event_id)
		with self.fs.open(filename, 'wb') as f:
			f.write(event_json)


if __name__ == "__main__":
	timeline = TimeLine('__default__', '/tmp/timeline')

	timeline.add_event('TEXT', text="Hello, World!", title="Greeting")

	events = timeline.get_events()
	from pprint import pprint
	pprint(events)
