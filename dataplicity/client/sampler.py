from __future__ import unicode_literals
from __future__ import print_function

from dataplicity import errors
from dataplicity.compat import py2bytes

from time import time
import os
from os.path import join, getsize, abspath, dirname, exists
from functools import partial
from threading import RLock
import struct


class SamplerError(Exception):
    pass


class NoSamplerError(KeyError):
    pass


class SamplerManager(object):
    def __init__(self, path):
        self.path = path
        self.samplers = {}

    def get_sampler(self, sampler_name):
        """Get a named sampler"""
        try:
            sampler = self.samplers[sampler_name]
        except KeyError:
            raise NoSamplerError("No sampler called {!r}".format(sampler_name))
        return sampler

    @classmethod
    def init_from_conf(cls, client, conf):

        samplers_path = conf.get('samplers', 'path', '/tmp/dataplicity/samplers/')
        sampler_manager = cls(samplers_path)

        for section, name in conf.qualified_sections('sampler'):
            if not conf.get_bool(section, 'enabled', True):
                continue
            time_format = conf.get(section, 'time_format', 'd')
            value_format = conf.get(section, 'value_format', 'd')
            max_samples = conf.get_integer(section, 'max_sample', 10000)
            path = join(dirname(conf.path), samplers_path, client.device_class, name)
            try:
                os.makedirs(path)
            except OSError:
                pass
            else:
                client.log.debug("created {}".format(path))

            sampler = Sampler(path,
                              name,
                              time_format=time_format,
                              value_format=value_format,
                              max_samples=max_samples)
            sampler_manager.add_sampler(name, sampler)
            client.log.debug("initialized sampler '{}'".format(name))
        return sampler_manager

    def add_sampler(self, name, sampler):
        """Register a new sampler"""
        if name in self.samplers:
            raise errors.ConfigError("sampler '{}' is already registered".format(name))
        self.samplers[name] = sampler

    def sample(self, sampler_name, timestamp, value):
        """Add a sample to the given sampler"""
        self.get_sampler(sampler_name).add_sample(timestamp, value)

    def sample_now(self, sampler_name, value):
        """Add a sample to the given sampler, with the current time"""
        self.get_sampler(sampler_name).add_sample(time(), value)

    def enumerate_samplers(self):
        """Get the names of all the samplers"""
        return sorted(self.samplers.keys())


class Sampler(object):
    def __init__(self, path, name, time_format='d', value_format='d', max_samples=1000):
        self.path = abspath(path)
        self.name = name
        self.time_format = time_format
        self.value_format = value_format
        self.max_samples = max_samples

        self.samples_path = join(path, 'samples.smp')
        self.samples_snapshot_path = join(path, 'samples.smp.snapshot')

        sample_format = self.sample_format = '<' + time_format + value_format
        sample_struct = self.sample_struct = struct.Struct(py2bytes(sample_format))
        self.sample_pack = sample_struct.pack
        self.sample_unpack = sample_struct.unpack
        self.sample_size = sample_struct.size

        self.max_file_size = len(self.header) + self.sample_size * self.max_samples

        self.lock = RLock()

        self.check_create()
        super(Sampler, self).__init__()

    @property
    def header(self):
        """Header is text based, the rest of the file is binary. No validation is done at the moment,
        but this format is future proofed for expansion."""
        return b"sampler v1\n" + self.sample_format.encode('utf-8') + b'\n'

    @classmethod
    def _read_header(self, f):
        """Read the sampler header from a file object"""
        f.readline()  # First line reserved for expansion
        # Second line contains struct format
        return f.readline().rstrip(b'\n')

    @property
    def full(self):
        """Check if the sampler has more than the maximum number of samples"""
        return getsize(self.samples_path) >= self.max_file_size

    def check_create(self):
        """Create an empty sampler if it doesn't already exist"""
        with self.lock:
            if not exists(self.samples_path):
                try:
                    os.makedirs(dirname(self.samples_path))
                except:
                    pass
                with open(self.samples_path, 'wb') as f:
                    f.write(self.header)

    def read_samples(self, samples_path=None):
        """Read and unpack all the samples in to a list of tuples (timestamp, value)"""
        # N.B. Doesn't lock
        if samples_path is None:
            samples_path = self.samples_path
        with open(samples_path, 'rb') as f:
            sample_format = self._read_header(f).decode('utf-8')
            sample_struct = struct.Struct(py2bytes(sample_format))
            sample_size = sample_struct.size
            read_sample = partial(f.read, sample_size)
            unpack = sample_struct.unpack
            samples = [unpack(sample) for sample in iter(read_sample, b'')]
        return samples

    def reset(self):
        """Reset samples"""
        with self.lock:
            with open(self.samples_path, 'wb') as f:
                f.write(self.header)

    def add_sample(self, timestamp, value):
        """Add a sample, return True if the sample was added.
        A return value of False indicates the sampler file has reached the maximum number of samples allowed.

        """
        if self.full:
            # Stop sampling when the file is full
            return False
        with self.lock:
            with open(self.samples_path, 'ab') as f:
                f.write(self.sample_pack(timestamp, value))
        return True

    def snapshot_samples(self):
        """Take a snapshot of samples for syncing, so that sampling may continue uninterrupted"""
        # A snapshot is a copy of the current samples file
        # Once it has been synced it can be deleted
        if not exists(self.samples_snapshot_path):
            with self.lock:
                self.check_create()
                if not exists(self.samples_snapshot_path):
                    os.rename(self.samples_path, self.samples_snapshot_path)
                self.check_create()
        return self.read_samples(self.samples_snapshot_path)

    def remove_snapshot(self):
        """Remove any samples snapshot"""
        try:
            os.remove(self.samples_snapshot_path)
        except OSError:
            pass


if __name__ == "__main__":
    from time import time
    sampler = Sampler('./testsampler', 'hobbits')
    sampler.add_sample(time(), 1.0)
    sampler.add_sample(time(), 1.1)
    sampler.add_sample(time(), 1.4)
    sampler.add_sample(time(), 1.7)
    sampler.add_sample(time(), 1.10)
    print(sampler.read_samples())
    sampler.reset()
    print(sampler.read_samples())
