import pytest
from hypothesis import given
from hypothesis.strategies import text, integers, characters, one_of
from hypothesis.strategies import sampled_from

from trojan_linter.linter import lint_text, LineMap, ALLOWED_CONTROL_CHARS
from trojan_linter.nits import ControlChar


clean_ascii_text = text(one_of(
    characters(min_codepoint=32, max_codepoint=126),
    sampled_from(ALLOWED_CONTROL_CHARS),
))


@given(clean_ascii_text)
def test_clean_ascii(text):
    assert list(lint_text('test', text)) == []


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
    nits = list(lint_text('test', text))
    print(nits)
    assert len(nits) == 1
    nit = nits[0]
    assert isinstance(nit, ControlChar)
    assert nit.index == pos


@given(
    text(characters(
        whitelist_categories=('Co', 'Cf', 'Cn', 'Cc'),
        blacklist_characters=ALLOWED_CONTROL_CHARS,
    )),
)
def test_all_control_chars(text):
    nits = list(lint_text('test', text))
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
        list(lint_text('test', text))
