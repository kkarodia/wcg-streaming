import setuptools
import os
import sys

try:
    import multiprocessing  # noqa
except ImportError:
    pass

setuptools.setup(
    name='wcg-transcript',
    version='0.1',
    setup_requires=['pbr>=1.8'],
    pbr=True,
    install_requires=[
        'requests',
        'sounddevice',
    ]
)
