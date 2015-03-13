from __future__ import unicode_literals
from __future__ import print_function

import unittest

from dataplicity.client import Client

import os.path

tests_dir = os.path.dirname(__file__)


class TestClient(unittest.TestCase):
    """Test initialization and closing of Client"""

    def test_create(self):
        """Test creating a client"""
        client = Client([os.path.join(tests_dir, 'projects/simple/dataplicity.conf')], create_m2m=False)
        client.close()

    def test_samplers(self):
        """Test a client with samplers"""
        client = Client([os.path.join(tests_dir, 'projects/samplers/dataplicity.conf')], create_m2m=False)
        client.samplers.sample_now('test', 101)
        sampler = client.samplers.get_sampler('test')
        for t, v in sampler.snapshot_samples():
            self.assertEqual(v, 101)
        client.close()

    def test_timeline(self):
        """Test a client with a timeline"""
        TEXT = "Explicit is better than implicit."
        client = Client([os.path.join(tests_dir, 'projects/timeline/dataplicity.conf')], create_m2m=False)
        timeline = client.timelines.get_timeline('cam')
        timeline.clear_all()
        event = timeline.new_event('TEXT', timestamp=100000, text=TEXT)
        event.write()
        events = timeline.get_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['text'], TEXT)
        client.close()
