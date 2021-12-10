import tokenize as py_tokenize
import token as token_info
import dataclasses
import difflib
import io

from .nits import Token


TOKEN_TYPE_MAP = {
    token_info.ENDMARKER: 'space',
    token_info.NUMBER: 'number',
    token_info.NEWLINE: 'space',
    token_info.NL: 'space',
    token_info.NAME: 'name',
    token_info.OP: 'op',
    token_info.ERRORTOKEN: 'op',
    token_info.COMMENT: 'comment',
    token_info.INDENT: 'space',
    token_info.DEDENT: 'space',
    token_info.STRING: 'string',
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
        yield Token(
            source, linemap,
            type=TOKEN_TYPE_MAP[token.type],
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
