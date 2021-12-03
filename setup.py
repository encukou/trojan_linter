import sys
import subprocess
import shlex
from shutil import which

from setuptools import setup, Extension


if which('pkg-config'):
    cflags = shlex.split(subprocess.run(
        ['pkg-config', 'icu-uc', '--cflags'],
        text=True,
        stdout=subprocess.PIPE,
    ).stdout)

    ldflags = shlex.split(subprocess.run(
        ['pkg-config', 'icu-uc', '--libs'],
        text=True,
        stdout=subprocess.PIPE,
    ).stdout)
else:
    cflags = []
    ldflags = ['-licuuc']


if sys.version_info >= (3, 10):
    limited_args = {
        'py_limited_api': True,
        'define_macros': [('Py_LIMITED_API', '0x030A0000')],
    }
else:
    limited_args = {}


setup(
    ext_modules=[
        Extension(
            'trojan_linter._linter',
            ['linter_module.c'],
            extra_compile_args=cflags,
            extra_link_args=ldflags,
            **limited_args,
        )
    ],
)
