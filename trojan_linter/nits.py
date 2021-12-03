class Nit:
    def __init__(self, source, linemap, index):
        self.source = source
        self.linemap = linemap
        self.index = index
        self.row, self.col = linemap.index_to_row_col(index)

class ControlChar(Nit):
    pass
