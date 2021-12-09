from functools import cached_property
import unicodedata


def safe_char_repr(char):
    codepoint = ord(char)
    if 32 <= codepoint < 127:
        return char
    if codepoint <= 0xff:
        return f'\\x{codepoint:02x}'
    if codepoint <= 0xffff:
        return f'\\u{codepoint:04x}'
    return f'\\U{codepoint:08x}'


class Nit:
    def __init__(self, source, linemap, index):
        self.source = source
        self.linemap = linemap
        self.index = index
        self.row, self.col = linemap.index_to_row_col(index)

    def __repr__(self):
        return f"<{type(self).__name__} @ {self.row}:{self.col}>"

    def __init_subclass__(cls):
        cls.name = cls.__name__

class NonASCII(Nit):
    def __init__(self, source, linemap, token, ascii_lookalike, nfkc, control_match):
        super().__init__(source, linemap, token.start_index)
        self.token = token
        self.token_type = token.type
        self.string = token.string
        self.ascii_lookalike = ascii_lookalike
        self.nfkc = nfkc
        self.control_index = self.index + control_match.start(0) if control_match else None

class PrecisFail(Nit):
    def __init__(self, source, linemap, token, reason):
        super().__init__(source, linemap, token.start_index)
        self.token = token
        self.token_type = token.type
        self.string = token.string
        self.reason = reason

    @cached_property
    def nfkc(self):
        return unicodedata.normalize('NFKC', self.string)

class ReorderedToken(Nit):
    def __init__(self, source, linemap, token, reordered, reordered_char_in_token):
        super().__init__(source, linemap, token.start_index)
        self.token = token
        self.token_type = token.type
        self.string = token.string
        self.reordered = reordered
        self.reordered_char_in_token = reordered_char_in_token

    @cached_property
    def reordered_repr(self):
        lines = [
            'The token is:',
            f'    {"".join(safe_char_repr(c) for c in self.string)}',
            'but appears as:',
        ]
        reprs = [safe_char_repr(c) for c in self.reordered]
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

class ReorderedLine(Nit):
    def __init__(self, source, linemap, lineno, string, reordered, reordered_char_in_token):
        super().__init__(source, linemap, linemap.row_col_to_index(lineno, 0))
        self.lineno = lineno
        self.string = string
        self.reordered = reordered
        self.reordered_char_in_token = reordered_char_in_token
