from bisect import bisect_right

class LineMap:
    """Maps text indices to (line, column) pairs and vice versa"""

    def __init__(self, source):
        lines = source.splitlines(keepends=True)
        self.line_starts = []
        current_pos = 0
        for line in lines:
            self.line_starts.append(current_pos)
            current_pos += len(line)
        if not lines:
            self.line_starts.append(current_pos)

    def index_to_row_col(self, index):
        lineno = bisect_right(self.line_starts, index)
        line_start = self.line_starts[lineno - 1]
        return lineno, index - line_start

    def row_col_to_index(self, row, col):
        line_start = self.line_starts[row - 1]
        return line_start + col
