# trojan_linter

Checks Python source files for possible surprises related to Unicode,
such as those explained in [PEP 672].

[PEP 672]: https://www.python.org/dev/peps/pep-0672/


## This is an early preview!

The tool might not do what you want it to do.
Feel free to report issues!


## Installation

This package needs ICU development files installed on your system,
either findable with `pkg-config` or in default locations.

If you have that, you can install it with:

    pip install trojan_linter


## Use

and run with:

    python -m trojan_linter FILENAME

Several filenames can be given.
If a directory is given, it is searched recursively for `*.py` files.


## No API

This project doesn't have any stable Python API.
Use the command-line interface.


## License

This project is released under the MIT license, see `LICENSE.MIT`.
May it serve you well.
