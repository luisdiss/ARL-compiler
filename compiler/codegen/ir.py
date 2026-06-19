from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Temp:
    """A compiler-generated temporary holding an intermediate value."""
    n: int

    def __str__(self) -> str:
        return f"t{self.n}"


@dataclass
class Const:
    """A literal constant (number, string, or bool) as it appears in source."""
    value: str

    def __str__(self) -> str:
        return self.value


# An operand is either a temporary register or an inline constant.
Operand = Temp | Const


@dataclass
class IRBinOp:
    dest: Temp
    left: Operand
    op: str
    right: Operand

    def __str__(self) -> str:
        return f"  {self.dest} = {self.left} {self.op} {self.right}"


@dataclass
class IRUnaryOp:
    dest: Temp
    op: str
    src: Operand

    def __str__(self) -> str:
        return f"  {self.dest} = {self.op}{self.src}"


@dataclass
class IRLoad:
    """Load a named variable from its stack slot into a temporary."""
    dest: Temp
    var: str

    def __str__(self) -> str:
        return f"  {self.dest} = load {self.var}"


@dataclass
class IRStore:
    """Store a value into a named variable's stack slot."""
    var: str
    src: Operand

    def __str__(self) -> str:
        return f"  store {self.var} = {self.src}"


@dataclass
class IRCompare:
    """Produce a boolean temporary (1 = true, 0 = false) from a comparison."""
    dest: Temp
    left: Operand
    op: str
    right: Operand

    def __str__(self) -> str:
        return f"  {self.dest} = {self.left} {self.op} {self.right}"


@dataclass
class IRLabel:
    name: str

    def __str__(self) -> str:
        return f"{self.name}:"


@dataclass
class IRJump:
    label: str

    def __str__(self) -> str:
        return f"  jump {self.label}"


@dataclass
class IRCondJump:
    """Branch on a boolean temporary produced by IRCompare or IRBinOp(and)."""
    cond: Temp
    true_label: str
    false_label: str

    def __str__(self) -> str:
        return f"  if {self.cond} goto {self.true_label} else {self.false_label}"


@dataclass
class IRCall:
    """Call a named function; dest is None when the return value is discarded."""
    dest: Optional[Temp]
    func: str
    args: list[Operand] = field(default_factory=list)

    def __str__(self) -> str:
        args_str = ", ".join(str(a) for a in self.args)
        prefix = f"{self.dest} = " if self.dest is not None else ""
        return f"  {prefix}call {self.func}({args_str})"


@dataclass
class IRReturn:
    value: Optional[Operand] = None

    def __str__(self) -> str:
        return f"  return {self.value}" if self.value is not None else "  return"


@dataclass
class IRFuncBegin:
    name: str
    params: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"func {self.name}({', '.join(self.params)}):"


@dataclass
class IRFuncEnd:
    name: str

    def __str__(self) -> str:
        return f"end {self.name}"
