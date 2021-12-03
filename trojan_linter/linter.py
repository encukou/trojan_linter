from bisect import bisect_right
import unicodedata
import re

from . import nits
from . import _linter as c_linter
from .confusables import ascii_confusable_map

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
        self.line_starts.append(current_pos)

    def index_to_row_col(self, index):
        lineno = bisect_right(self.line_starts, index)
        line_start = self.line_starts[lineno - 1]
        return lineno, index - line_start

    def row_col_to_index(self, row, col):
        line_start = self.line_starts[row - 1]
        return line_start + col


def lint_text(name, text, tokenizer):
    linemap = None
    def _get_linemap():
        nonlocal linemap
        if linemap is None:
            linemap = LineMap(text)
        return linemap

    if text.isascii():
        # Only handle control chars
        for match in ASCII_CONTROL_RE.finditer(text):
            yield nits.ControlChar(text, _get_linemap(), match.start())
        return

    linemap = _get_linemap()

    nit_tuples, bidimap = c_linter.process_source(text)
    for name, *args in nit_tuples:
        yield getattr(nits, name)(text, linemap, *args)

    for token in tokenizer(text, linemap):
        if not token.string.isascii():
            ascii_lookalike = None
            in_nfd = unicodedata.normalize('NFD', token.string)
            mapped = in_nfd.translate(ascii_confusable_map)
            if mapped.isascii():
                ascii_lookalike = mapped
            yield nits.NonASCII(text, _get_linemap(), token, ascii_lookalike)
