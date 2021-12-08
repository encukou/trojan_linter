import unicodedata
from ast import literal_eval
from textwrap import dedent
import re

import pytest
from hypothesis import given, assume
from hypothesis.strategies import text, integers, characters, one_of
from hypothesis.strategies import sampled_from

from trojan_linter.linter import lint_text, LineMap, ALLOWED_CONTROL_CHARS
from trojan_linter.nits import ControlChar, safe_char_repr
from trojan_linter.tokenize_python import tokenize


clean_ascii_text = text(one_of(
    characters(min_codepoint=32, max_codepoint=126),
    sampled_from(ALLOWED_CONTROL_CHARS),
))


@given(clean_ascii_text)
def test_clean_ascii(text):
    assert list(lint_text('test', text, tokenize)) == []


@given(
    clean_ascii_text,
    integers(0),
    characters(
        whitelist_categories=('Co', 'Cf', 'Cn', 'Cc'),
        blacklist_characters=ALLOWED_CONTROL_CHARS,
    ),
)
def test_control_chars(text, pos, control):
    pos %= len(text) + 1
    text = text[:pos] + control + text[pos:]
    try:
        nits = list(lint_text('test', text, tokenize))
    except SyntaxError:
        with pytest.raises(SyntaxError):
            compile(text, 'test', 'exec')
        assume(False)
    print(nits)
    assert len(nits) >= 1
    nit = nits[0]
    assert isinstance(nit, ControlChar)
    assert nit.index == pos
    assert unicodedata.category(text[nit.index]).startswith('C')


@given(
    text(characters(
        whitelist_categories=('Co', 'Cf', 'Cn', 'Cc'),
        blacklist_characters=ALLOWED_CONTROL_CHARS,
    )),
)
def test_all_control_chars(text):
    nits = list(lint_text('test', text, tokenize))
    print(nits)
    assert len(nits) >= len(text)
    for nit in nits[:len(text)]:
        assert isinstance(nit, ControlChar)


@given(
    clean_ascii_text,
    integers(0),
    characters(
        whitelist_categories=['Cs'],
    ),
)
def test_surrogates(text, pos, control):
    pos %= len(text) + 1
    text = text[:pos] + control + text[pos:]
    with pytest.raises(UnicodeError):
        list(lint_text('test', text, tokenize))


CASES = {
    's\N{CYRILLIC SMALL LETTER ES}ope': [
        {
            'name': 'NonASCII',
            'string': 's\N{CYRILLIC SMALL LETTER ES}ope',
            'token_type': 'name',
            'ascii_lookalike': 'scope',
        },
    ],
    'u"s\N{CYRILLIC SMALL LETTER ES}ope"': [
        {
            'name': 'NonASCII',
            'string': 'u"s\N{CYRILLIC SMALL LETTER ES}ope"',
            'token_type': 'string',
            'ascii_lookalike': 'u"scope"',
        },
    ],
    '\N{CYRILLIC CAPITAL LETTER ZHE}ohn': [
        {
            'name': 'NonASCII',
            'string': '\N{CYRILLIC CAPITAL LETTER ZHE}ohn',
            'token_type': 'name',
            'ascii_lookalike': None,
        },
    ],
    "names = 'x\u02BB, \u02BBy' ": [
        {
            'name': 'NonASCII',
            'string': "'x\u02BB, \u02BBy'",
            'token_type': 'string',
            'ascii_lookalike': "'x', 'y'",
        },
    ],
    "names = 'x\u02BB', '\u02BBy' ": [
        {
            'name': 'NonASCII',
            'string': "'x\u02BB'",
            'token_type': 'string',
            'ascii_lookalike': "'x''",
        },
        {
            'name': 'NonASCII',
            'string': "'\u02BBy'",
            'token_type': 'string',
            'ascii_lookalike': "''y'",
        },
    ],
    "int('৪୨')": [
        {
            'name': 'NonASCII',
            'string': "'৪୨'",
            'token_type': 'string',
            'ascii_lookalike': "'89'",
        },
    ],
    "'\N{HEBREW LETTER ALEF}\N{HEBREW LETTER GIMEL}'": [
        {'name': 'NonASCII', 'string': "'\N{HEBREW LETTER ALEF}\N{HEBREW LETTER GIMEL}'"},
        {
            'name': 'ReorderedToken',
            'string': "'\N{HEBREW LETTER ALEF}\N{HEBREW LETTER GIMEL}'",
            'reordered': "'\N{HEBREW LETTER GIMEL}\N{HEBREW LETTER ALEF}'",
            'token_type': 'string',
        },
    ],
    """'zz\N{HEBREW LETTER ALEF} -' + '- \N{HEBREW LETTER GIMEL}zz'""": [
        {'name': 'NonASCII'},
        {
            'name': 'ReorderedToken',
            'string': "'zz\N{HEBREW LETTER ALEF} -'",
            'reordered_repr': dedent(r"""
                The token is:
                    'zz\u05d0 -'
                but appears as:
                    'zz\u05d2 -' + '- \u05d0
                    ^^^            ^^^^^^^^^
                    (characters without ^ below aren't part of the token)
                where:
                    \u05d2 is HEBREW LETTER GIMEL
                    \u05d0 is HEBREW LETTER ALEF
            """).strip(),
            'reordered': "'zz\N{HEBREW LETTER GIMEL} -' + '- \N{HEBREW LETTER ALEF}",
            'token_type': 'string',
        },
        {'name': 'NonASCII'},
        {
            'name': 'ReorderedToken',
            'string': "'- \N{HEBREW LETTER GIMEL}zz'",
            'reordered_repr': dedent(r"""
                The token is:
                    '- \u05d2zz'
                but appears as:
                    \u05d2 -' + '- \u05d0zz'
                    ^^^^^^^^^            ^^^
                    (characters without ^ below aren't part of the token)
                where:
                    \u05d2 is HEBREW LETTER GIMEL
                    \u05d0 is HEBREW LETTER ALEF
            """).strip(),
            'reordered': "\N{HEBREW LETTER GIMEL} -' + '- \N{HEBREW LETTER ALEF}zz'",
            'token_type': 'string',
        },
    ],
    "'\N{HEBREW LETTER ALEF}' * 1_9 + '\N{HEBREW LETTER ALEF}'": [
        {'name': 'NonASCII', 'string': "'\N{HEBREW LETTER ALEF}'"},
        {
            'name': 'ReorderedToken',
            'string': "1_9",
            'reordered': "9_1",
            'token_type': 'number',
        },
        {'name': 'NonASCII', 'string': "'\N{HEBREW LETTER ALEF}'"},
    ],
}

@pytest.mark.parametrize('source', CASES)
def test_cases(source):
    expected = CASES[source]
    nits = list(lint_text('test', source, tokenize))
    print(nits)
    assert len(nits) == len(expected)
    for nit, exp in zip(nits, expected):
        for attr, value in exp.items():
            assert getattr(nit, attr) == value


@given(characters(blacklist_characters="'\\"))
def test_safe_char_repr(char):
    result = safe_char_repr(char)
    assert literal_eval("'" + result + "'") == char
    assert re.fullmatch(r'[ -~]+', result)
