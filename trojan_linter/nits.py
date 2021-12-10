try:
    from functools import cached_property
except ImportError:
    cached_property = property


def safe_char_repr(char, min_passthru=32):
    codepoint = ord(char)
    if min_passthru <= codepoint < 127:
        return char
    if codepoint <= 0xff:
        return f'\\x{codepoint:02x}'
    if codepoint <= 0xffff:
        return f'\\u{codepoint:04x}'
    return f'\\U{codepoint:08x}'

def safe_char_reprs(string):
    if string.startswith(' ') or string.endswith(' '):
        min_passthru = 33
    else:
        min_passthru = 32
    return [safe_char_repr(char, min_passthru) for char in string]


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
        return ''.join(safe_char_reprs(self.string))

class Token(CodePart):
    def __init__(self, source, linemap, type, string, start_index, end_index):
        super().__init__(source, linemap, start_index, end_index)
        self.type = type
        self.string = string

    def __repr__(self):
        return f"<{self.name}({self.type})@{self.row}:{self.col}: {self._repr_nits()}>"


class Line(CodePart):
    def __init__(self, source, linemap, lineno):
        start_index = linemap.row_col_to_index(lineno, 0)
        end_index = linemap.row_col_to_index(lineno + 1, 0)
        super().__init__(source, linemap, start_index, end_index)
        self.lineno = lineno

    @cached_property
    def string(self):
        return self.source[self.start_index:self.end_index]

    def __repr__(self):
        return f"<{type(self).__name__} {self.row}: {self._repr_nits()}>"


class File(CodePart):
    def __init__(self, source, linemap):
        super().__init__(source, linemap, 0, len(source))
        self.string = source

    def __repr__(self):
        return f"<{type(self).__name__}: {self._repr_nits()}>"


class Nit:
    def __init__(self, code_part):
        self.code_part = code_part

    def __repr__(self):
        return f"<{type(self).__name__}>"

    def __init_subclass__(cls):
        cls.name = cls.__name__

class ControlCharacter(Nit):
    def __init__(self, code_part, offset):
        super().__init__(code_part)
        self.offset = offset
        i = self.code_part.start_index + offset
        self.control_char = self.code_part.source[i]

class _Reordered(Nit):
    def __init__(self, code_part, reordered, reordered_char_in_token):
        super().__init__(code_part)
        self.reordered = reordered
        self.reordered_char_in_token = reordered_char_in_token

    @cached_property
    def _reordered_safe_char_reprs(self):
        return safe_char_reprs(self.reordered)

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


class ReorderedToken(_Reordered):
    pass

class ReorderedLine(_Reordered):
    pass

class NonASCII(Nit):
    def __init__(self, code_part):
        super().__init__(code_part)

class ASCIILookalike(Nit):
    def __init__(self, code_part, lookalike):
        super().__init__(code_part)
        self.lookalike = lookalike

class HasLookalike(Nit):
    def __init__(self, code_part, other_token):
        super().__init__(code_part)
        self.other_token = other_token

class NonNFKC(Nit):
    def __init__(self, code_part, normalized):
        super().__init__(code_part)
        self.normalized = normalized

    @cached_property
    def normalized_safe(self):
        return ''.join(safe_char_reprs(self.normalized))

class PolicyFail(Nit):
    def __init__(self, code_part, reason):
        super().__init__(code_part)
        self.reason = reason

class UnusualEncoding(Nit):
    def __init__(self, code_part, encoding):
        super().__init__(code_part)
        self.encoding = encoding

'''
    @cached_property
    def reordered_repr(self):
        lines = [
            'The token is:',
            f'    {"".join(safe_char_reprs(self.string))}',
            'but appears as:',
        ]
        reprs = safe_char_reprs(self.reordered)
        lines.append(f'    {"".join(reprs)}')
        if not all(self.reordered_char_in_token):
            lines.append('    ' + ''.join(
                ('^' if isin else ' ') * len(crepr)
                for isin, crepr in zip(self.reordered_char_in_token, reprs)
            ))
            lines.append("    (characters without ^ below aren't part of the token)")
        legend = []
        seen = set()
        for char, crepr in zip(self.reordered, reprs):
            try:
                name = unicodedata.name(char)
            except ValueError:
                continue
            if crepr != char and char not in seen:
                legend.append(f'    {crepr} is {name}')
                seen.add(char)
        if legend:
            lines.append('where:')
            lines.extend(legend)
        return '\n'.join(lines)
'''
