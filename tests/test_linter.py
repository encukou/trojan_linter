import unicodedata
from ast import literal_eval
import re

import pytest
from hypothesis import given, assume
from hypothesis.strategies import text, integers, characters, one_of
from hypothesis.strategies import sampled_from

from trojan_linter.linter import lint_text, ALLOWED_CONTROL_CHARS
from trojan_linter.nits import safe_char_repr, safe_char_reprs
from trojan_linter.profiles import PythonProfile, TestingProfile


clean_ascii_text = text(one_of(
    characters(min_codepoint=32, max_codepoint=126),
    sampled_from(ALLOWED_CONTROL_CHARS),
))


@given(clean_ascii_text)
def test_clean_ascii(text):
    assert list(lint_text('test', text, TestingProfile)) == []


@given(
    clean_ascii_text,
    integers(0),
    one_of(
        characters(
            whitelist_categories=('Co', 'Cf', 'Cc'),
            blacklist_characters=ALLOWED_CONTROL_CHARS,
        ),
        # Include an unassigned character. 'Cn' category is problematic
        # as it depends on the Unicode version.
        sampled_from('\U0001FF80'),
    )
)
def test_control_chars(text, pos, control):
    pos %= len(text) + 1
    text = text[:pos] + control + text[pos:]
    try:
        bad_parts = list(lint_text('test', text, TestingProfile()))
    except SyntaxError:
        with pytest.raises((SyntaxError, ValueError)):
            compile(text, 'test', 'exec')
        assume(False)
    print(bad_parts)
    assert len(bad_parts) >= 1
    num_cc_nits = 0
    for bp in bad_parts:
        for nit in bp.nits_by_name('ControlCharacter'):
            assert nit.control_char == control
            assert bp.string[nit.offset] == control
            assert text[bp.start_index + nit.offset] == control
            num_cc_nits += 1
    assert num_cc_nits == 1


@given(
    text(one_of(
        characters(
            whitelist_categories=('Co', 'Cf', 'Cc'),
            blacklist_characters=ALLOWED_CONTROL_CHARS,
        ),
        sampled_from('\U0001FF80'),
    )),
)
def test_all_control_chars(text):
    bad_parts = list(lint_text('test', text, TestingProfile()))
    found_controls = []
    for bp in bad_parts:
        for nit in bp.nits_by_name('ControlCharacter'):
            assert unicodedata.category(nit.control_char).startswith('C')
            found_controls.append(nit.control_char)
    assert sorted(text) == sorted(found_controls)


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
        list(lint_text('test', text, TestingProfile()))


CASES = {
    's\N{CYRILLIC SMALL LETTER ES}ope': [
        {
            'name': 'Token',
            'type': 'name',
            'row': 1,
            'col': 0,
            'start_index': 0,
            'start': (1, 0),
            'end_index': 5,
            'end': (2, 0),  # XXX
            'string': 's\N{CYRILLIC SMALL LETTER ES}ope',
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ASCIILookalike',
                    'lookalike': 'scope',
                },
            ],
        },
    ],
    'u"s\N{CYRILLIC SMALL LETTER ES}ope"': [
        {
            'name': 'StringToken',
            'type': 'string',
            'py_delimiter': '"',
            'py_content': 's\N{CYRILLIC SMALL LETTER ES}ope',
            'py_flags': {'u'},
            'row': 1,
            'col': 0,
            'start_index': 0,
            'start': (1, 0),
            'end_index': 8,
            'end': (2, 0),
            'string': 'u"s\N{CYRILLIC SMALL LETTER ES}ope"',
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ASCIILookalike',
                    'lookalike': 'u"scope"',
                },
            ],
        },
    ],
    '\N{CYRILLIC CAPITAL LETTER ZHE}ohn': [
        {
            'name': 'Token',
            'type': 'name',
            'string': '\N{CYRILLIC CAPITAL LETTER ZHE}ohn',
            'nits': [
                {'name': 'NonASCII'},
            ],
        },
    ],
    "names = 'x\u02BB, \u02BBy' ": [
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'x\u02BB, \u02BBy'",
            'py_delimiter': "'",
            'py_content': 'x\u02BB, \u02BBy',
            'py_flags': set(),
            'row': 1,
            'col': 8,
            'start_index': 8,
            'start': (1, 8),
            'end_index': 16,
            'end': (1, 16),
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ASCIILookalike',
                    'lookalike': "'x', 'y'",
                },
            ],
        },
    ],
    "names = 'x\u02BB', '\u02BBy' ": [
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'x\u02BB'",
            'py_delimiter': "'",
            'py_content': 'x\u02BB',
            'py_flags': set(),
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ASCIILookalike',
                    'lookalike': "'x''",
                },
            ],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'\u02BBy'",
            'py_delimiter': "'",
            'py_content': '\u02BBy',
            'py_flags': set(),
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ASCIILookalike',
                    'lookalike': "''y'",
                },
            ],
        },
    ],
    "int('৪୨')": [
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'৪୨'",
            'py_delimiter': "'",
            'py_content': '৪୨',
            'py_flags': set(),
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ASCIILookalike',
                    'lookalike': "'89'",
                },
            ],
        },
    ],
    "'\N{HEBREW LETTER ALEF}\N{HEBREW LETTER GIMEL}'": [
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'\N{HEBREW LETTER ALEF}\N{HEBREW LETTER GIMEL}'",
            'string_safe': r"'\u05d0\u05d2'",
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ReorderedToken',
                    'reordered': "'\N{HEBREW LETTER GIMEL}\N{HEBREW LETTER ALEF}'",
                    'reordered_safe': r"'\u05d2\u05d0'",
                    'reordered_safe_underline': None,
                },
            ],
        },
        {
            'name': 'Line',
            'string': "'\N{HEBREW LETTER ALEF}\N{HEBREW LETTER GIMEL}'",
            'string_safe': r"'\u05d0\u05d2'",
            'nits': [
                {
                    'name': 'ReorderedLine',
                    'reordered': "'\N{HEBREW LETTER GIMEL}\N{HEBREW LETTER ALEF}'",
                    'reordered_safe': r"'\u05d2\u05d0'",
                    'reordered_safe_underline': None,
                },
            ],
        },
    ],
    """'zz\N{HEBREW LETTER ALEF} -' + '- \N{HEBREW LETTER GIMEL}zz'""": [
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'zz\N{HEBREW LETTER ALEF} -'",
            'string_safe': r"'zz\u05d0 -'",
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ReorderedToken',
                    'reordered': "'zz\N{HEBREW LETTER GIMEL} -' + '- \N{HEBREW LETTER ALEF}",
                    'reordered_safe': r"'zz\u05d2 -' + '- \u05d0",
                    'reordered_safe_underline':
                                      r"^^^            ^^^^^^^^^",
                },
            ],
        },
        {
            # XXX
            'name': 'Line',
            'string': """'zz\N{HEBREW LETTER ALEF} -' + '- \N{HEBREW LETTER GIMEL}zz'""",
            'string_safe': r"""'zz\u05d0 -' + '- \u05d2zz'""",
            'nits': [
                {
                    'name': 'ReorderedLine',
                    'reordered': """'zz\N{HEBREW LETTER GIMEL} -' + '- \N{HEBREW LETTER ALEF}zz'""",
                    'reordered_safe': r"""'zz\u05d2 -' + '- \u05d0zz'""",
                    'reordered_safe_underline': None,
                },
            ],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'- \N{HEBREW LETTER GIMEL}zz'",
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ReorderedToken',
                    'reordered': "\N{HEBREW LETTER GIMEL} -' + '- \N{HEBREW LETTER ALEF}zz'",
                    'reordered_safe': r"\u05d2 -' + '- \u05d0zz'",
                    'reordered_safe_underline':
                                      r"^^^^^^^^^            ^^^",
                },
            ],
        },
    ],
    "'\N{HEBREW LETTER ALEF}' * 1_9 + '\N{HEBREW LETTER ALEF}'": [
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'\N{HEBREW LETTER ALEF}'",
            'nits': [
                {'name': 'NonASCII'},
            ],
        },
        {
            'name': 'Line',
            'string': "'\N{HEBREW LETTER ALEF}' * 1_9 + '\N{HEBREW LETTER ALEF}'",
            'nits': [
                {
                    'name': 'ReorderedLine',
                    'reordered': "'\N{HEBREW LETTER ALEF}' + 9_1 * '\N{HEBREW LETTER ALEF}'",
                    'reordered_safe': r"'\u05d0' + 9_1 * '\u05d0'",
                    'reordered_safe_underline': None,
                },
            ],
        },
        {
            'name': 'Token',
            'type': 'number',
            'string': "1_9",
            'string_safe': "1_9",
            'nits': [
                {
                    'name': 'ReorderedToken',
                    'reordered': "9_1",
                    'reordered_safe': r"9_1",
                    'reordered_safe_underline': None,
                },
            ],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'\N{HEBREW LETTER ALEF}'",
            'nits': [
                {'name': 'NonASCII'},
            ],
        },
    ],
    "\N{HEBREW LETTER ALEF} + \N{HEBREW LETTER GIMEL}": [
        {
            'name': 'Token',
            'type': 'name',
            'string': "\N{HEBREW LETTER ALEF}",
            'nits': [
                {'name': 'NonASCII'},
            ],
        },
        {
            'name': 'Line',
            'lineno': 1,
            'nits': [
                {
                    'name': 'ReorderedLine',
                    'reordered': "\N{HEBREW LETTER GIMEL} + \N{HEBREW LETTER ALEF}",
                    'reordered_safe': r"\u05d2 + \u05d0",
                    'reordered_safe_underline': None,
                },
            ],
        },
        {
            'name': 'Token',
            'type': 'name',
            'string': "\N{HEBREW LETTER GIMEL}",
            'nits': [
                {'name': 'NonASCII'},
            ],
        },
    ],
    "\N{LATIN SMALL LIGATURE FI} = 'u\N{COMBINING DIAERESIS}'": [
        {
            'name': 'Token',
            'type': 'name',
            'string': "\N{LATIN SMALL LIGATURE FI}",
            'nits': [
                {
                    'name': 'PolicyFail',
                    'reason': "DISALLOWED/has_compat",
                },
                {'name': 'NonASCII'},
                {
                    'name': 'ASCIILookalike',
                    'lookalike': "fi",
                },
                {
                    'name': 'NonNFKC',
                    'normalized': "fi",
                    'normalized_safe': "fi",
                },
            ],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'u\N{COMBINING DIAERESIS}'",
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'NonNFKC',
                    'normalized': "'\N{LATIN SMALL LETTER U WITH DIAERESIS}'",
                    'normalized_safe': r"'\xfc'",
                },
            ],
        },
    ],
    "print(len((lambda x,\N{HANGUL FILLER}: (\N{HANGUL FILLER},))(1, 2)))": 2*[
        {
            'name': 'Token',
            'type': 'name',
            'string': "\N{HANGUL FILLER}",
            'nits': [
                {
                    'name': 'PolicyFail',
                    'reason': "DISALLOWED/precis_ignorable_properties",
                },
                {'name': 'NonASCII'},
                {
                    'name': 'NonNFKC',
                    'normalized': "\N{HANGUL JUNGSEONG FILLER}",
                    'normalized_safe': r"\u1160",
                },
            ],
        },
    ],
    "'\U0001FF80'": [
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'\U0001FF80'",
            'nits': [
                {
                    'name': 'PolicyFail',
                    'reason': "DISALLOWED/unassigned",
                },
                {
                    'name': 'ControlCharacter',
                    'offset': 1,
                    'control_char': "\U0001FF80",
                },
                {'name': 'NonASCII'},
            ],
        },
    ],
    """
        \N{KELVIN SIGN}lock
        Klock
    """: [
        {
            'name': 'Token',
            'type': 'name',
            'string': "\N{KELVIN SIGN}lock",
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ASCIILookalike',
                    'lookalike': "Klock",
                },
                {
                    'name': 'NonNFKC',
                    'normalized': "Klock",
                    'normalized_safe': r"Klock",
                },
            ],
        },
        {
            'name': 'Token',
            'type': 'name',
            'string': "Klock",
            'nits': [
                {
                    'name': 'HasLookalike',
                    'other_token': {
                        'name': 'Token',
                        'type': 'name',
                        'string': "\N{KELVIN SIGN}lock"
                    },
                },
            ],
        },
    ],
    """
        '''\N{LATIN SMALL LETTER U WITH DIAERESIS}'''
        u'\N{LATIN SMALL LETTER U WITH DIAERESIS}'
        u"\N{LATIN SMALL LETTER U WITH DIAERESIS}"
        rf'\N{LATIN SMALL LETTER U WITH DIAERESIS}'
        b'\N{LATIN SMALL LETTER U WITH DIAERESIS}'
        r'\N{LATIN SMALL LETTER U WITH DIAERESIS}'
        fr'\N{LATIN SMALL LETTER U WITH DIAERESIS}'
    """: [
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'''\N{LATIN SMALL LETTER U WITH DIAERESIS}'''",
            'py_delimiter': "'''",
            'py_content': '\N{LATIN SMALL LETTER U WITH DIAERESIS}',
            'py_flags': set(),
            'nits': [{'name': 'NonASCII'}],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "u'\N{LATIN SMALL LETTER U WITH DIAERESIS}'",
            'py_delimiter': "'",
            'py_content': '\N{LATIN SMALL LETTER U WITH DIAERESIS}',
            'py_flags': {'u'},
            'nits': [{'name': 'NonASCII'}],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': 'u"\N{LATIN SMALL LETTER U WITH DIAERESIS}"',
            'py_delimiter': '"',
            'py_content': '\N{LATIN SMALL LETTER U WITH DIAERESIS}',
            'py_flags': {'u'},
            'nits': [{'name': 'NonASCII'}],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "rf'\N{LATIN SMALL LETTER U WITH DIAERESIS}'",
            'py_delimiter': "'",
            'py_content': '\N{LATIN SMALL LETTER U WITH DIAERESIS}',
            'py_flags': {'r', 'f'},
            'nits': [{'name': 'NonASCII'}],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "b'\N{LATIN SMALL LETTER U WITH DIAERESIS}'",
            'py_delimiter': "'",
            'py_content': '\N{LATIN SMALL LETTER U WITH DIAERESIS}',
            'py_flags': {'b'},
            'nits': [{'name': 'NonASCII'}],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "r'\N{LATIN SMALL LETTER U WITH DIAERESIS}'",
            'py_delimiter': "'",
            'py_content': '\N{LATIN SMALL LETTER U WITH DIAERESIS}',
            'py_flags': {'r'},
            'nits': [{'name': 'NonASCII'}],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "fr'\N{LATIN SMALL LETTER U WITH DIAERESIS}'",
            'py_delimiter': "'",
            'py_content': '\N{LATIN SMALL LETTER U WITH DIAERESIS}',
            'py_flags': {'r', 'f'},
            'nits': [{'name': 'HasLookalike'}, {'name': 'NonASCII'}],
        },
    ],
    """
        fi
        f'\N{LATIN SMALL LIGATURE FI}'
        hasattr(foo, '\N{LATIN SMALL LIGATURE FI}')
    """: [
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "f'\N{LATIN SMALL LIGATURE FI}'",
            'nits': [
                {
                    'name': 'PolicyFail',
                    'reason': "DISALLOWED/has_compat",
                },
                {'name': 'NonASCII'},
                {
                    'name': 'ASCIILookalike',
                    'lookalike': "f'fi'",
                },
                {
                    'name': 'NonNFKC',
                    'normalized': "f'fi'",
                },
            ],
        },
        {
            'name': 'StringToken',
            'type': 'string',
            'string': "'\N{LATIN SMALL LIGATURE FI}'",
            'nits': [
                {'name': 'NonASCII'},
                {
                    'name': 'ASCIILookalike',
                    'lookalike': "'fi'",
                },
                {
                    'name': 'NonNFKC',
                    'normalized': "'fi'",
                },
            ],
        },
    ],
}

@pytest.mark.parametrize('source', CASES)
def test_cases(source):
    expected = CASES[source]
    bad_parts = list(lint_text('test', source, PythonProfile()))
    assert_result_matches(bad_parts, expected)

def assert_result_matches(got, expected, path=''):
    if isinstance(expected, list):
        assert len(got) == len(expected)
        for i, (g, e) in enumerate(zip(got, expected)):
            assert_result_matches(g, e, f'{path}[{i}]')
    elif isinstance(expected, dict):
        for attr_name, e in expected.items():
            assert_result_matches(
                getattr(got, attr_name), e, f'{path}.{attr_name}',
            )
    else:
        assert expected == got

@given(characters(blacklist_characters="'\\"))
def test_safe_char_repr(char):
    chars_to_explain = {}
    result = safe_char_repr(char, chars_to_explain)
    assert literal_eval("'" + result + "'") == char
    assert re.fullmatch(r'[ -~]+', result)
    if result == char:
        assert chars_to_explain == {}
    else:
        assert chars_to_explain == {char: result}


@given(text(characters(blacklist_characters='\\"')))
def test_safe_char_reprs(text):
    chars_to_explain = {}
    result = "".join(safe_char_reprs(text, chars_to_explain))
    assert literal_eval('"' + result + '"') == text
    assert re.fullmatch(r'[ -~]*', result)
    assert not result.startswith(' ')
    assert not result.endswith(' ')
    if result == text:
        assert chars_to_explain == {}
