class Nit:
    def __init__(self, source, linemap, index):
        self.source = source
        self.linemap = linemap
        self.index = index
        self.row, self.col = linemap.index_to_row_col(index)

    def __repr__(self):
        return f"<{type(self).__name__} @ {self.row}:{self.col}>"

    def __init_subclass__(cls):
        cls.name = cls.__name__

class ControlChar(Nit):
    pass

class NonASCII(Nit):
    def __init__(self, source, linemap, token, ascii_lookalike):
        super().__init__(source, linemap, token.start_index)
        self.token = token
        self.token_type = token.type
        self.string = token.string
        self.ascii_lookalike = ascii_lookalike
