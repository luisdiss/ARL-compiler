from typing import NamedTuple


class SourcePos(NamedTuple):
    line: int
    col: int

    def __str__(self) -> str:
        return f"line {self.line}, col {self.col}"


class CompilationError(Exception):
    def __init__(self, *args, errors: list['CompilationError'] | None = None):
        self._errors = errors
        if errors is not None and not args:
            msgs = "\n".join(f"  {e}" for e in errors)
            super().__init__(f"{len(errors)} error(s):\n{msgs}")
        else:
            super().__init__(*args)

    @property
    def errors(self) -> list['CompilationError']:
        return self._errors if self._errors is not None else [self]


class SourceError(CompilationError):
    def __init__(self, message: str, pos: SourcePos):
        self.pos = pos
        super().__init__(f"{message} ({pos})")


class LexError(SourceError):
    pass


class ParseError(SourceError):
    pass


class SemanticError(CompilationError):
    pass

