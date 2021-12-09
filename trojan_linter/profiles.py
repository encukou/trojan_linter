import tokenize as py_tokenize

import precis_i18n

from . import tokenize_python

class Profile:
    pass

opaque_precis_profile = precis_i18n.get_profile('OpaqueString')
username_precis_profile = precis_i18n.get_profile('UsernameCasePreserved')
nickname_precis_profile = precis_i18n.get_profile('NicknameCasePreserved')

class TestingProfile(Profile):
    tokenize = tokenize_python.tokenize
    def read_file(self, filename):
        with py_tokenize.open(filename) as f:
            return filename.read()

    token_string_profiles = {
        'name': str,
        'string': str,
        'op': str,
        'newline': str,
        'space': str,
        'number': str,
        'comment': str,
    }

class PythonProfile(Profile):
    tokenize = tokenize_python.tokenize
    def read_file(self, filename):
        with py_tokenize.open(filename) as f:
            return filename.read()

    token_string_profiles = {
        'name': username_precis_profile.enforce,
        'string': str,
        'op': str,
        'newline': str,
        'space': str,
        'number': str,
        'comment': str,
    }
