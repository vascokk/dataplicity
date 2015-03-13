from __future__ import unicode_literals
from __future__ import print_function

import unittest
import tempfile
import shutil

import os

from dataplicity.client.sampler import Sampler


class TestSamplers(unittest.TestCase):
    """
    Check samples

    The sampler system supports a variety of time / value formats.

    We don't check every possible combination, since some just don't make sense. (byte for the time for example).

    At some point we should restrict the time / value formats to sensible values.

    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp('dptest')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_samplers(self):
        """Test sampler read/write in various formats"""

        test_signed_integer_samples = [
            (1.0, 1),
            (1000.0, 2),
            (2000.0, 4),
            (3000.0, 8),
            (4000.0, -2),
            (5000.0, -4),
            (6000.0, -8),
        ]

        test_unsigned_integer_samples = [
            (0.0, 1),
            (1000.0, 2),
            (2000.0, 4),
            (3000.0, 8),
        ]

        test_float_samples = [
            (1.0, 1.0),
            (1000.0, 2.0),
            (2000.0, 4.0),
            (3000.0, 8.0),
            (5000.0, -2.0),
            (6000.0, -4.0),
            (7000.0, -8.0),
            (8001.0, 1.1),
            (8003.0, 3.1),
            (8007.0, 7.34),
        ]

        def do_check(prefix, time_format, test_samples, formats):

            def compare(a, b):
                if isinstance(a, float):
                    # Check floating point values compare within tolerance
                    return abs(a - b) < 0.00001
                return a == b

            for fmt in formats:

                path = os.path.join(self.temp_dir, 'sampler_{}_{}_{}'.format(prefix, time_format, fmt))
                os.mkdir(path)

                sampler = Sampler(path, "sampler_" + fmt, time_format=time_format, value_format=fmt)
                sampler.check_create()

                # Write some samples
                for t, v in test_samples:
                    print(repr(t), repr(v))
                    sampler.add_sample(t, v)

                # Check they can be read back
                samples = sampler.read_samples()

                for (t, v), (st, sv) in zip(test_samples, samples):
                    assert compare(t, st)
                    assert compare(v, sv)

                # Take a snapshot, check the samples
                samples = sampler.snapshot_samples()

                for (t, v), (st, sv) in zip(test_samples, samples):
                    assert compare(t, st)
                    assert compare(v, sv)

                # Remove the snapshot, check it is empty
                sampler.remove_snapshot()

                samples = sampler.snapshot_samples()
                self.assertEqual(len(samples), 0)

                # Add samples again
                for t, v in test_samples:
                    sampler.add_sample(t, v)

                # Check they can be read
                samples = sampler.read_samples()

                for (t, v), (st, sv) in zip(test_samples, samples):
                    assert compare(t, st)
                    assert compare(v, sv)

        for time_format in ['d', 'f', 'i', 'l']:
            def convert(s):
                if time_format in "df":
                    return [(float(t), v) for t, v in s]
                else:
                    return [(int(t), v) for t, v in s]
            do_check('signed', time_format, convert(test_signed_integer_samples), ['h', 'l', 'q'])
            do_check('unsigned', time_format, convert(test_unsigned_integer_samples), ['h', 'l', 'q'])
            do_check('float', time_format, convert(test_float_samples), ['f', 'd'])
