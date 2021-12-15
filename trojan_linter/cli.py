from pathlib import Path

import click

from .linter import lint_path
from trojan_linter.profiles import PythonProfile


@click.command()
@click.argument('paths', metavar='FILENAME...', nargs=-1, type=Path)
def main(paths):
    """Check source code for potential Unicode-related surprises
    """
    fail = False
    for path in paths:
        for code_part in lint_path(path, PythonProfile()):
            print(code_part.format())
            fail = True

    if fail:
        exit(1)
