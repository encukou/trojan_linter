import tokenize as py_tokenize
import token as token_info
import io

try:
    from functools import cached_property
except ImportError:
    cached_property = property

import regex

from .nits import Token

STRING_RE = regex.compile(
    r'''(?P<flags>[^'"]*)(?P<delim>('|"){3}|'(?!')|"(?!"))(?P<content>.*)(?P=delim)''',
    regex.DOTALL,
)

class StringToken(Token):
    @cached_property
    def _py_info(self):
        return STRING_RE.fullmatch(self.string).groupdict()

    @cached_property
    def py_delimiter(self):
        return self._py_info['delim']

    @cached_property
    def py_content(self):
        return self._py_info['content']

    @cached_property
    def py_flags(self):
        return set(self._py_info['flags'].lower())



TOKEN_TYPE_MAP = {
    token_info.ENDMARKER: ('space', Token),
    token_info.NUMBER: ('number', Token),
    token_info.NEWLINE: ('space', Token),
    token_info.NL: ('space', Token),
    token_info.NAME: ('name', Token),
    token_info.OP: ('op', Token),
    token_info.ERRORTOKEN: ('op', Token),
    token_info.COMMENT: ('comment', Token),
    token_info.INDENT: ('space', Token),
    token_info.DEDENT: ('space', Token),
    token_info.STRING: ('string', StringToken),
}

def generate_tokens(source):
    try:
        yield from py_tokenize.generate_tokens(io.StringIO(source).readline)
    except py_tokenize.TokenError:
        raise SyntaxError('tokenizer failed')


def tokenize(source, linemap):
    last_end_index = 0
    for token in generate_tokens(source):
        if token.type == token_info.ENDMARKER:
            assert token.start == token.end
            continue
        if token.type == token_info.DEDENT:
            assert token.start >= token.end
            continue
        start_index = linemap.row_col_to_index(*token.start)
        end_index = linemap.row_col_to_index(*token.end)
        if last_end_index < start_index:
            yield Token(
                source, linemap,
                type='space',
                string=source[last_end_index:start_index],
                start_index=last_end_index,
                end_index=start_index,
            )
        tok_type_name, tok_class = TOKEN_TYPE_MAP[token.type]
        yield tok_class(
            source, linemap,
            type=tok_type_name,
            string=token.string,
            start_index=start_index,
            end_index=end_index,
        )
        last_end_index = end_index
    eof_index = len(source) + 1
    if last_end_index < eof_index:
        yield Token(
            source, linemap,
            type='space',
            string=source[last_end_index:],
            start_index=last_end_index,
            end_index=eof_index,
        )
