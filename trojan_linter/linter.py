from bisect import bisect_right
import unicodedata
import regex
import io
import struct

from . import nits
from . import _linter as c_linter
from .confusables import ascii_confusable_map

ALLOWED_CONTROL_CHARS = '\t\n\v\f\r'
ASCII_CONTROL_RE = regex.compile(
    r'[[\0-\x1F\x7F]--[%s]]' % ALLOWED_CONTROL_CHARS,
    regex.V1,
)
ANY_CONTROL_RE = regex.compile(
    r'[[\p{C}]--[%s]]' % ALLOWED_CONTROL_CHARS,
    regex.V1,
)

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


def lint_text(name, text, tokenizer, token_string_profiles):
    linemap = None
    def _get_linemap():
        nonlocal linemap
        if linemap is None:
            linemap = LineMap(text)
        return linemap

    if text.isascii() and not ASCII_CONTROL_RE.search(text):
        return

    linemap = _get_linemap()

    bidi_l2v_map, bidi_v2l_map = c_linter.process_source(text)

    if bidi_l2v_map:
        bidi_l2v_map = memoryview(bidi_l2v_map).cast(INT32_FORMAT)
        bidi_v2l_map = memoryview(bidi_v2l_map).cast(INT32_FORMAT)
        # print('l2v', list(bidi_l2v_map))
        # print('v2l', list(bidi_v2l_map))

    # {token_type: {normalized_string: token}}
    seen_tokens = {}

    last_visual_start = -1
    reordered_lines = set()
    for token in tokenizer(text, linemap):
        if token.string:
            try:
                normalized = token_string_profiles[token.type](token.string)
            except UnicodeEncodeError as e:
                token.nits.append(nits.PolicyFail(token, e.reason))
                normalized = None
            if normalized is not None:
                seen = seen_tokens.setdefault(token.type, {})
                previous_token = seen.get(normalized)
                if previous_token and previous_token.string != token.string:
                    token.nits.append(nits.HasLookalike(token, previous_token))
                else:
                    seen[normalized] = token

        control_match = ANY_CONTROL_RE.search(token.string)
        if control_match:
            token.nits.append(nits.ControlCharacter(
                token, control_match.start()))
        if not token.string.isascii():
            token.nits.append(nits.NonASCII(token))
            nfd = unicodedata.normalize('NFD', token.string)
            mapped = nfd.translate(ascii_confusable_map)
            if mapped.isascii() and mapped != token.string:
                token.nits.append(nits.ASCIILookalike(token, mapped))

            nfkc = unicodedata.normalize('NFKC', token.string)
            if nfkc != token.string:
                token.nits.append(nits.NonNFKC(token, nfkc))

        if bidi_l2v_map:
            if len(token.string) > 1:
                reordered_string, reordered_char_in_token = _reorder_string(
                    text, bidi_l2v_map, bidi_v2l_map,
                    token.start_index,
                    token.start_index + len(token.string),
                )
                if reordered_string != token.string:
                    token.nits.append(nits.ReorderedToken(
                        token, reordered_string,
                        reordered_char_in_token,
                    ))

            start_index = token.start_index
            if start_index >= len(bidi_l2v_map):
                start_index = len(bidi_l2v_map) - 1
            visual_start = bidi_l2v_map[start_index]
            if visual_start < last_visual_start:
                lineno = token.start[0]
                if token.start[1] == 0:
                    lineno -= 1
                if lineno not in reordered_lines:
                    line = nits.Line(text, linemap, lineno)
                    reordered_string, reordered_char_in_token = _reorder_string(
                        text, bidi_l2v_map, bidi_v2l_map,
                        line.start_index,
                        line.end_index,
                    )
                    line.nits.append(nits.ReorderedLine(
                        line, reordered_string, reordered_char_in_token,
                    ))
                    yield line
                    reordered_lines.add(lineno)
            last_visual_start = visual_start

        if token.nits:
            yield token


def _reorder_string(text, bidi_l2v_map, bidi_v2l_map, start_index, end_index):
    logical_indices = range(start_index, end_index)
    visual_indices = [bidi_l2v_map[i] for i in logical_indices]
    visual_indices_set = set(visual_indices)
    reordered_visual_indices = range(
        min(visual_indices), max(visual_indices) + 1)
    reordered_logical_indices = [
        bidi_v2l_map[i] for i in reordered_visual_indices
    ]
    reordered_string = ''.join(text[i] for i in reordered_logical_indices)
    reordered_char_in_token = [
        i in visual_indices_set for i in reordered_visual_indices
    ]
    return reordered_string, reordered_char_in_token


