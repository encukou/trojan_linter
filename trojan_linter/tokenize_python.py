import tokenize as py_tokenize
import token as token_info
import dataclasses
import difflib

LineAndColumn = tuple[int, int]

@dataclasses.dataclass
class Token:
    type: str
    _py_type: int
    string: str
    start: LineAndColumn
    end: LineAndColumn
    start_index: int
    end_index: int

TOKEN_TYPE_MAP = {
    token_info.ENDMARKER: 'space',
    token_info.NUMBER: 'number',
    token_info.NEWLINE: 'newline',
    token_info.NL: 'newline',
    token_info.NAME: 'name',
    token_info.OP: 'op',
    token_info.ERRORTOKEN: 'op',
    token_info.COMMENT: 'comment',
    token_info.INDENT: 'space',
    token_info.DEDENT: 'space',
    token_info.STRING: 'string',
}

def generate_tokens(source):
    lines = source.splitlines(keepends=True)
    readline = iter(lines).__next__
    try:
        yield from py_tokenize.generate_tokens(readline)
    except py_tokenize.TokenError:
        raise SyntaxError('tokenizer failed')


def tokenize(source, linemap):
    last_end = 1, 0
    last_end_index = 0
    print("",last_end_index, repr(source))
    for token in generate_tokens(source):
        if token.type == token_info.ENDMARKER:
            assert token.start == token.end
            continue
        if token.type == token_info.DEDENT:
            assert token.start >= token.end
            continue
        start_index = linemap.row_col_to_index(*token.start)
        start = linemap.index_to_row_col(start_index)
        end_index = linemap.row_col_to_index(*token.end)
        end = linemap.index_to_row_col(end_index)
        if last_end_index < start_index:
            yield Token(
                'space',
                None,
                source[last_end_index : start_index],
                last_end,
                start,
                last_end_index,
                start_index,
            )
        yield Token(
            TOKEN_TYPE_MAP[token.type],
            token.type,
            token.string,
            start,
            end,
            start_index,
            end_index,
        )
        last_end = end
        last_end_index = end_index
    end = len(source) + 1
    print(last_end_index, end, repr(source))
    if last_end_index < end:
        yield Token(
            'space',
            None,
            source[last_end_index:],
            last_end,
            linemap.index_to_row_col(end),
            last_end_index,
            end,
        )
