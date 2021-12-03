from bisect import bisect_right
import re
import unicodedata

from . import nits

ALLOWED_CONTROL_CHARS = '\t\n\v\f\r'
ASCII_CONTROL_RE = re.compile(r'[\0-\x08\x0E-\x1F\x7F]')


class LineMap:
    """Maps text indices to (line, column) pairs and vice versa"""

    def __init__(self, source):
        lines = source.splitlines(keepends=True)
        self.line_starts = []
        current_pos = 0
        for line in lines:
            self.line_starts.append(current_pos)
            current_pos += len(line)
        if not lines:
            self.line_starts.append(current_pos)

    def index_to_row_col(self, index):
        lineno = bisect_right(self.line_starts, index)
        line_start = self.line_starts[lineno - 1]
        return lineno, index - line_start

    def row_col_to_index(self, row, col):
        line_start = self.line_starts[row - 1]
        return line_start + col


def lint_text(name, text):
    linemap = None
    def _get_linemap():
        nonlocal linemap
        if linemap is None:
            linemap = LineMap(text)
            return linemap

    if text.isascii():
        for match in ASCII_CONTROL_RE.finditer(text):
            yield nits.ControlChar(text, _get_linemap(), match.start())
        return

    for index, char in enumerate(text):
        if unicodedata.category(char).startswith('C') and char not in ALLOWED_CONTROL_CHARS:
            yield nits.ControlChar(text, _get_linemap(), index)
