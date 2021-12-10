import tokenize as py_tokenize

import precis_i18n

from . import tokenize_python

class Profile:
    pass

_opaque_precis_profile = precis_i18n.get_profile('OpaqueString')
_username_precis_profile = precis_i18n.get_profile('UsernameCasePreserved')

def ascii_token_profile(token):
    if not token.string.isascii():
        raise ValueError('Not ASCII')
    return token.string

def opaque_token_profile(token):
    try:
        return _opaque_precis_profile.enforce(token.string)
    except UnicodeEncodeError as e:
        raise ValueError(e.reason)

def username_token_profile(token):
    try:
        return _username_precis_profile.enforce(token.string)
    except UnicodeEncodeError as e:
        raise ValueError(e.reason)

def python_string_profile(token):
    if 'f' in token.py_flags:
        profile = _username_precis_profile
    else:
        profile = _opaque_precis_profile
    try:
        return profile.enforce(token.py_content)
    except UnicodeEncodeError as e:
        raise ValueError(e.reason)

class TestingProfile(Profile):
    tokenize = tokenize_python.tokenize
    def read_file(self, filename):
        with py_tokenize.open(filename) as file:
            return file.read()

    token_profiles = {
        'name': str,
        'string': str,
        'op': str,
        'space': str,
        'number': str,
        'comment': str,
    }

class PythonProfile(Profile):
    tokenize = tokenize_python.tokenize
    def read_file(self, filename):
        with py_tokenize.open(filename) as file:
            return file.read()

    token_profiles = {
        'name': username_token_profile,
        'string': python_string_profile,
        'op': ascii_token_profile,
        'space': ascii_token_profile,
        'number': ascii_token_profile,
        'comment': opaque_token_profile,
    }
