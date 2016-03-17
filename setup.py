#!/usr/bin/env python

from setuptools import setup, find_packages

classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Programming Language :: Python',
]

# http://stackoverflow.com/questions/2058802/how-can-i-get-the-version-defined-in-setup-py-setuptools-in-my-package
with open('dataplicity/_version.py') as f:
    exec(f.read())

with open('README.md') as f:
    long_desc = f.read()

setup(
    name='dataplicity',
    version=VERSION,
    description="Platform for connected devices",
    long_description=long_desc,
    author='WildFoundry',
    author_email='support@dataplicity.com',
    url='https://www.dataplicity.com',
    platforms=['any'],
    packages=find_packages(),
    classifiers=classifiers,

    entry_points={
        "console_scripts": [
           'dataplicity = dataplicity.app:main'
        ]
    },

    install_requires=[
        'websocket-client',
        'fs>=0.5.0',
        'enum34',
        'six',
        'python-daemon==2.1.1',
    ]
)
