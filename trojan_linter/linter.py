from bisect import bisect_right
import unicodedata
import re
import io
import struct

from . import nits
from . import _linter as c_linter
from .confusables import ascii_confusable_map

ALLOWED_CONTROL_CHARS = '\t\n\v\f\r'
ASCII_CONTROL_RE = re.compile(r'[\0-\x08\x0E-\x1F\x7F]')

for INT32_FORMAT in '@i', '@l', '@q':
    if struct.calcsize(INT32_FORMAT) == 4:
        break
else:
    raise SystemError(f'could not find struct format for native int32')

class LineMap:
    """Maps text indices to (line, column) pairs and vice versa"""

    def __init__(self, source):
        self.line_starts = []
        current_pos = 0
        for line in io.StringIO(source):
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

    nit_tuples, bidi_l2v_map, bidi_v2l_map = c_linter.process_source(text)
    for name, *args in nit_tuples:
        yield getattr(nits, name)(text, linemap, *args)

    if bidi_l2v_map:
        bidi_l2v_map = memoryview(bidi_l2v_map).cast(INT32_FORMAT)
        bidi_v2l_map = memoryview(bidi_v2l_map).cast(INT32_FORMAT)
        print('l2v', list(bidi_l2v_map))
        print('v2l', list(bidi_v2l_map))

    for token in tokenizer(text, linemap):
        if not token.string.isascii():
            ascii_lookalike = None
            nfkc = unicodedata.normalize('NFKC', token.string)
            nfd = unicodedata.normalize('NFD', token.string)
            mapped = nfd.translate(ascii_confusable_map)
            if mapped.isascii():
                ascii_lookalike = mapped
            yield nits.NonASCII(text, linemap, token, ascii_lookalike, nfkc)

        if bidi_l2v_map and len(token.string) > 1:
            logical_indices = range(token.start_index, token.start_index+len(token.string))
            visual_indices = [bidi_l2v_map[i] for i in logical_indices]
            visual_indices_set = set(visual_indices)
            reordered_visual_indices = range(
                min(visual_indices), max(visual_indices) + 1)
            reordered_logical_indices = [bidi_v2l_map[i] for i in reordered_visual_indices]
            reordered_string = ''.join(text[i] for i in reordered_logical_indices)
            reordered_char_in_token = [i in visual_indices_set for i in reordered_visual_indices]
            if reordered_string != token.string:
                yield nits.ReorderedToken(text, linemap, token, reordered_string, reordered_char_in_token)
