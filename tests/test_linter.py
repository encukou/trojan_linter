import unicodedata

import pytest
from hypothesis import given, assume
from hypothesis.strategies import text, integers, characters, one_of
from hypothesis.strategies import sampled_from

from trojan_linter.linter import lint_text, LineMap, ALLOWED_CONTROL_CHARS
from trojan_linter.nits import ControlChar
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
    assert len(nits) == 1
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
    assert len(nits) == len(text)
    for nit in nits:
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
            'name': 'NonAscii',
            'string': 'sc\N{CYRILLIC SMALL LETTER ES}pe',
            'token': 'name',
            'ascii_lookalike': 'scope'
        },
    ],
}

@pytest.mark.parametrize('source', CASES)
def test_cases(source):
    expected = CASES[source]
    nits = list(lint_text('test', source, tokenize))
    print(nits)
    assert len(nits) == len(expected)
    for nit, exp in zip(source, expected):
        for attr, value in expected.items():
            assert getattr(nit, name) == value
