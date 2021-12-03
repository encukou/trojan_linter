import pytest
from hypothesis import given, example, assume
from hypothesis.strategies import text, characters, one_of
from hypothesis.strategies import sampled_from

from trojan_linter.linter import LineMap
from trojan_linter.tokenize_python import tokenize


@given(text())
@example("coding: ascii")
def test_coverage(text):
    linemap = LineMap(text)
    last_pos = 1, 0
    last_index = 0
    strings = []
    try:
        tokens = list(tokenize(text, linemap))
    except SyntaxError:
        with pytest.raises((SyntaxError, ValueError)):
            compile(text, 'test', 'exec')
        assume(False)
    for token in tokens:
        print(token)
        assert token.start == last_pos
        assert token.end >= last_pos
        last_pos = token.end
        assert token.start_index == last_index
        assert token.end_index >= last_index
        last_index = token.end_index
        assert token.string == text[token.start_index:token.end_index]
        strings += token.string
    assert last_index == len(text) + 1
    assert ''.join(strings) == text
