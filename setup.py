#!/usr/bin/env python
from setuptools import setup
from dataplicity import __version__ as VERSION

classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Programming Language :: Python',
]

long_desc = """An interface to Dataplicity platform"""

setup(name='dataplicity',
      version=VERSION,
      long_description=long_desc,
      author='Adixein',
      author_email='support@dataplicity.com',
      url='http://www.dataplicity.com',
      platforms=['any'],
      packages=['dataplicity',
                'dataplicity.app',
                'dataplicity.app.subcommands',
                'dataplicity.client',
                ],
      classifiers=classifiers,
      scripts=["dataplicity/app/dataplicity"],
      install_requires=['python-daemon',
                        'fs']
      #data_files=[("/etc/dataplicity", ["dataplicity/app/logging.conf"]), ],
      )
