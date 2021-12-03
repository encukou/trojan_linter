from hypothesis import given
from hypothesis.strategies import text, integers, characters

from trojan_linter.linter import LineMap


@given(text(characters(), min_size=1), integers(0))
def test_properties(source, index):
    index %= len(source)
    char = source[index]
    linemap = LineMap(source)
    row, col = linemap.index_to_row_col(index)
    print(index, row, col, repr(source), linemap.line_starts)

    # row_col_to_index should undo index_to_row_col
    assert linemap.row_col_to_index(row, col) == index

    # indexing by index should yield same value as by row/col
    assert char == source.splitlines(keepends=True)[row-1][col-1]


@given(text(characters()))
def test_past_end(source):
    index = len(source)
    linemap = LineMap(source)
    row, col = linemap.index_to_row_col(index)
    print(index, row, col, repr(source), linemap.line_starts)

    rows = source.splitlines(keepends=True) or ['']
    assert row == len(rows)
    assert col == len(rows[-1]) + 1
