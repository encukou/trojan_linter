import unicodedata

try:
    from functools import cached_property
except ImportError:
    cached_property = property


def safe_char_repr(char, chars_to_explain, min_passthru=32):
    codepoint = ord(char)
    if min_passthru <= codepoint < 127:
        return char
    if char == '\n':
        char_repr = '\\n'
    elif codepoint <= 0xff:
        char_repr = f'\\x{codepoint:02x}'
    elif codepoint <= 0xffff:
        char_repr = f'\\u{codepoint:04x}'
    else:
        char_repr = f'\\U{codepoint:08x}'
    chars_to_explain[char] = char_repr
    return char_repr

def safe_char_reprs(string, chars_to_explain):
    if string.startswith(' ') or string.endswith(' '):
        min_passthru = 33
    else:
        min_passthru = 32
    return [
        safe_char_repr(char, chars_to_explain, min_passthru)
        for char in string
    ]

def format_string(string, chars_to_explain):
    return ''.join(safe_char_reprs(string, chars_to_explain))

class CodePart:
    def __init__(self, source, linemap, start_index, end_index):
        self.source = source
        self.linemap = linemap
        self.start_index = start_index
        self.end_index = end_index
        self.nits = []

    def __init_subclass__(cls):
        cls.name = cls.__name__

    def __repr__(self):
        return f"<{self.name}@{self.row}:{self.col}: {self._repr_nits()}>"

    def _repr_nits(self):
        return ','.join(nit.name for nit in self.nits)

    def nits_by_name(self, name):
        return [nit for nit in self.nits if nit.name == name]

    @cached_property
    def start(self):
        return self.linemap.index_to_row_col(self.start_index)

    @cached_property
    def end(self):
        return self.linemap.index_to_row_col(self.end_index)

    @cached_property
    def row(self):
        return self.start[0]

    @cached_property
    def col(self):
        return self.start[1]

    @cached_property
    def string_safe(self):
        return ''.join(safe_char_reprs(self.string, {}))

    def format(self):
        chars_to_explain = {}
        lines = list(self.format_header(chars_to_explain))
        for nit in self.nits:
            lines.extend(nit.format_lines(chars_to_explain))
        if chars_to_explain:
            lines.append('  where:')
            for char, expanded in sorted(chars_to_explain.items()):
                try:
                    name = unicodedata.name(char)
                except ValueError:
                    name = 'unnnamed/unassigned'
                lines.append(f'    {expanded} is {name}')
        return '\n'.join(lines)

    def format_header(self):
        return f'{self.linemap.filename}: {self.name}'

class Token(CodePart):
    def __init__(self, source, linemap, type, string, start_index, end_index):
        super().__init__(source, linemap, start_index, end_index)
        self.type = type
        self.string = string

    def __repr__(self):
        return f"<{self.name}({self.type})@{self.row}:{self.col}: {self._repr_nits()}>"

    def format_header(self, chars_to_explain):
        filename = self.linemap.filename
        yield f'{filename}:{self.row}:{self.col}: WARNING: {self.type} token'
        yield '    ' + format_string(self.string, chars_to_explain)

class Line(CodePart):
    def __init__(self, source, linemap, lineno):
        start_index = linemap.row_col_to_index(lineno, 0)
        end_index = linemap.row_col_to_index(lineno + 1, 0)
        if source[end_index-1:end_index] == '\n':
            # Final newline isn't part of the string
            end_index -= 1
        super().__init__(source, linemap, start_index, end_index)
        self.lineno = lineno

    @cached_property
    def string(self):
        return self.source[self.start_index:self.end_index]

    def __repr__(self):
        return f"<{type(self).__name__} {self.row}: {self._repr_nits()}>"

    def format_header(self, chars_to_explain):
        filename = self.linemap.filename
        yield f'{filename}:{self.row}: WARNING: line {self.row}'
        yield '    ' + format_string(self.string, chars_to_explain)


class File(CodePart):
    def __init__(self, filename, source):
        super().__init__(source, None, 0, len(source))
        self.string = source
        self.filename = filename

    start = 0, 0
    end = 0, 0

    def __repr__(self):
        return f"<{type(self).__name__}: {self._repr_nits()}>"

    def format_header(self, chars_to_explain):
        filename = self.filename
        yield f'{filename}: WARNING: this file'


class Nit:
    def __repr__(self):
        return f"<{type(self).__name__}>"

    def __init_subclass__(cls):
        cls.name = cls.__name__

class ControlCharacter(Nit):
    def __init__(self, offset, control_char):
        self.offset = offset
        self.control_char = control_char

    def format_lines(self, chars_to_explain):
        yield '  contains a control character'
        yield '    (possibly invisible and/or affecting nearby text)'

class _Reordered(Nit):
    def __init__(self, reordered, reordered_char_in_token):
        self.reordered = reordered
        self.reordered_char_in_token = reordered_char_in_token

    @cached_property
    def _reordered_safe_char_reprs(self):
        return safe_char_reprs(self.reordered, {})

    @cached_property
    def reordered_safe(self):
        return ''.join(self._reordered_safe_char_reprs)

    @cached_property
    def reordered_safe_underline(self):
        if all(self.reordered_char_in_token):
            return None
        reprs = self._reordered_safe_char_reprs
        return ''.join(
            ('^' if isin else ' ') * len(crepr)
            for isin, crepr in zip(self.reordered_char_in_token, reprs)
        )

    def format_lines(self, chars_to_explain):
        yield '  is reordered; it appears as:'
        yield f'    {self.reordered_safe}'
        if not all(self.reordered_char_in_token):
            yield f'    {self.reordered_safe_underline}'
            yield "    (^ marks this text)"


class ReorderedToken(_Reordered):
    pass

class ReorderedLine(_Reordered):
    pass

class NonASCII(Nit):
    def format_lines(self, chars_to_explain):
        yield '  is not ASCII'

class ASCIILookalike(Nit):
    def __init__(self, lookalike):
        self.lookalike = lookalike

    def format_lines(self, chars_to_explain):
        yield '  looks like ASCII:'
        yield f'    {self.lookalike}'

class HasLookalike(Nit):
    def __init__(self, other_token):
        self.other_token = other_token

    def format_lines(self, chars_to_explain):
        ot = self.other_token
        yield f'  looks like {ot.type} on {ot.row}:{ot.col}:'
        yield f'    {format_string(ot.string, chars_to_explain)}'

class NonNFKC(Nit):
    def __init__(self, normalized):
        self.normalized = normalized

    @cached_property
    def normalized_safe(self):
        return format_string(self.normalized, {})

    def format_lines(self, chars_to_explain):
        yield '  is not NFKC normal form; normalizes to:'
        yield f'    {format_string(self.normalized, chars_to_explain)}'

class PolicyFail(Nit):
    def __init__(self, reason):
        self.reason = reason

    def format_lines(self, chars_to_explain):
        yield f'  fails policy: {self.reason}'

class UnusualEncoding(Nit):
    def __init__(self, encoding):
        self.encoding = encoding

    def format_lines(self, chars_to_explain):
        yield '  has an unusual encoding:'
        yield f'    {self.encoding}'
        yield '    (possibly hiding other issues in the source)'

class Unreadable(Nit):
    def __init__(self, problem):
        self.problem = problem

    def format_lines(self, chars_to_explain):
        yield f'  cannot be read: {self.problem}'
