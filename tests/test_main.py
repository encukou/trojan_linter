from pathlib import Path
import textwrap

import pytest
import yaml
from click.testing import CliRunner

from trojan_linter.cli import main

TEST_CASE_PATH = Path(__file__).parent / 'cases'
TEST_CASES = sorted(p.name for p in TEST_CASE_PATH.glob('*.yaml'))

@pytest.mark.parametrize('case_filename', TEST_CASES)
def test_file_case(case_filename, tmp_path, monkeypatch):
    with TEST_CASE_PATH.joinpath(case_filename).open() as file:
        data = yaml.safe_load(file)
    src_path = tmp_path / 'data.src'
    src_path.write_text(data['source'])

    print(src_path.read_bytes())
    print(src_path.read_text())

    runner = CliRunner(mix_stderr=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(main, [src_path.name])
    print(result)

    if result.exception and not isinstance(result.exception, SystemExit):
        raise result.exception

    assert result.exit_code == data.get('expected_exit_code', 1)
    assert result.stdout == data['expected_stdout']
    assert result.stderr == ''


def test_dir_of_files(tmp_path, monkeypatch):
    (tmp_path / 'dont_check_here.py').write_text('\x01')
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/source.py').write_text('\x02')
    (tmp_path / 'src/subdir').mkdir()
    (tmp_path / 'src/subdir/source1.py').write_text('\x03')
    (tmp_path / 'src/subdir/source2.py').write_text('\x04')
    (tmp_path / 'src/subdir/otherfile.bin').write_text('\x05')

    runner = CliRunner(mix_stderr=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(main, ['src/'])

    assert result.exit_code == 1
    assert result.stdout.strip() == textwrap.dedent(r"""
          src/source.py:1:0: WARNING: op token
              \x02
            contains a control character
              (possibly invisible and/or affecting nearby text)
            where:
              \x02 is unnnamed/unassigned
          src/subdir/source1.py:1:0: WARNING: op token
              \x03
            contains a control character
              (possibly invisible and/or affecting nearby text)
            where:
              \x03 is unnnamed/unassigned
          src/subdir/source2.py:1:0: WARNING: op token
              \x04
            contains a control character
              (possibly invisible and/or affecting nearby text)
            where:
              \x04 is unnnamed/unassigned
    """).strip()
    assert result.stderr == ''
