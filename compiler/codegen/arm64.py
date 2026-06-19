from __future__ import annotations
from typing import Any, Optional

from compiler.codegen.ir import (
    Temp, Const, Operand,
    IRBinOp, IRUnaryOp, IRLoad, IRStore, IRCompare,
    IRLabel, IRJump, IRCondJump, IRCall, IRReturn,
    IRFuncBegin, IRFuncEnd,
)


class ARM64Generator:
    """
    Translates an IR instruction list to ARM64 assembly (macOS / Apple Silicon).

    Strategy: every named variable and every temporary gets its own 8-byte slot
    on the stack.  x0/x1 are used as scratch registers within each instruction;
    all values are spilled immediately.  This is correct for all programs but not 
    optimal.

    Only 64-bit signed integer arithmetic is supported.  Float, string, and
    boolean values raise NotImplementedError.
    """

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._var_off: dict[str, int] = {}   # named var  → fp-relative offset
        self._temp_off: dict[int, int] = {}  # Temp.n     → fp-relative offset
        self._frame_size: int = 0


    # public

    def generate(self, ir: list) -> str:
        """Return an ARM64 .s string for the whole program."""
        top_level, functions = self._split(ir)

        self._line(".section __TEXT,__text")
        self._line(".global _main")
        self._line(".align 4")
        self._line("")

        for func_ir in functions:
            self._emit_func(func_ir)

        self._emit_main(top_level)

        return "\n".join(self._lines)


    # IR partitioning

    def _split(self, ir: list) -> tuple[list, list[list]]:
        top: list = []
        funcs: list[list] = []
        current: Optional[list] = None

        for instr in ir:
            if isinstance(instr, IRFuncBegin):
                current = [instr]
            elif isinstance(instr, IRFuncEnd):
                assert current is not None
                current.append(instr)
                funcs.append(current)
                current = None
            elif current is not None:
                current.append(instr)
            else:
                top.append(instr)

        return top, funcs


    # function generation

    def _emit_func(self, ir: list) -> None:
        begin: IRFuncBegin = ir[0]
        body: list = ir[1:-1]   # strip IRFuncBegin / IRFuncEnd

        self._setup_frame(begin.params, body)

        self._line(f"_{begin.name}:")
        self._prologue()

        # Store incoming argument registers to their stack slots.
        for i, param in enumerate(begin.params):
            if i >= 8:
                raise NotImplementedError("more than 8 parameters not supported")
            self._line(f"    str x{i}, [x29, #{self._var_off[param]}]")

        for instr in body:
            self._instr(instr)

        self._line("")

    def _emit_main(self, ir: list) -> None:
        self._setup_frame([], ir)
        self._line("_main:")
        self._prologue()

        for instr in ir:
            self._instr(instr)

        # Implicit return 0 from top-level.
        self._line("    mov x0, #0")
        self._restore_frame()
        self._line("")


    # frame layout

    def _setup_frame(self, params: list[str], body: list) -> None:
        """
        Assign a unique fp-relative (negative) offset to every named variable
        and every temporary that appears in this function's body.
        """
        self._var_off = {}
        self._temp_off = {}
        slot = -8   # first slot at [x29, #-8]

        for p in params:
            self._var_off[p] = slot
            slot -= 8

        for instr in body:
            if isinstance(instr, IRStore) and instr.var not in self._var_off:
                self._var_off[instr.var] = slot
                slot -= 8
            for t in self._collect_temps(instr):
                if t.n not in self._temp_off:
                    self._temp_off[t.n] = slot
                    slot -= 8

        used = (-slot - 8)          # bytes consumed by slots
        self._frame_size = (used + 15) & ~15  # round up to 16

    def _collect_temps(self, instr: Any) -> list[Temp]:
        """Return all Temp objects (dest and operands) referenced in instr."""
        out: list[Temp] = []
        for v in vars(instr).values():
            if isinstance(v, Temp):
                out.append(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, Temp):
                        out.append(item)
        return out


    # prologue / epilogue helpers

    def _prologue(self) -> None:
        self._line("    stp x29, x30, [sp, #-16]!")
        self._line("    mov x29, sp")
        if self._frame_size > 0:
            self._line(f"    sub sp, sp, #{self._frame_size}")

    def _restore_frame(self) -> None:
        """Emit the epilogue without moving a return value into x0."""
        self._line("    mov sp, x29")
        self._line("    ldp x29, x30, [sp], #16")
        self._line("    ret")


    # per-instruction translation

    def _instr(self, instr: Any) -> None:
        if isinstance(instr, IRLoad):
            self._line(f"    ldr x0, [x29, #{self._var_off[instr.var]}]")
            self._line(f"    str x0, [x29, #{self._temp_off[instr.dest.n]}]")

        elif isinstance(instr, IRStore):
            self._operand("x0", instr.src)
            self._line(f"    str x0, [x29, #{self._var_off[instr.var]}]")

        elif isinstance(instr, IRBinOp):
            self._operand("x0", instr.left)
            self._operand("x1", instr.right)
            asm_op = {"+": "add", "-": "sub", "*": "mul", "/": "sdiv",
                      "and": "and", "or": "orr"}.get(instr.op)
            if asm_op is None:
                raise NotImplementedError(f"binary op '{instr.op}'")
            self._line(f"    {asm_op} x0, x0, x1")
            self._line(f"    str x0, [x29, #{self._temp_off[instr.dest.n]}]")

        elif isinstance(instr, IRUnaryOp):
            self._operand("x0", instr.src)
            if instr.op == "-":
                self._line("    neg x0, x0")
            elif instr.op != "+":
                raise NotImplementedError(f"unary op '{instr.op}'")
            self._line(f"    str x0, [x29, #{self._temp_off[instr.dest.n]}]")

        elif isinstance(instr, IRCompare):
            self._operand("x0", instr.left)
            self._operand("x1", instr.right)
            self._line("    cmp x0, x1")
            cond = {"gt": "gt", "lt": "lt", "ge": "ge",
                    "le": "le", "eq": "eq", "ne": "ne"}.get(instr.op)
            if cond is None:
                raise NotImplementedError(f"comparison op '{instr.op}'")
            self._line(f"    cset x0, {cond}")
            self._line(f"    str x0, [x29, #{self._temp_off[instr.dest.n]}]")

        elif isinstance(instr, IRCondJump):
            self._line(f"    ldr x0, [x29, #{self._temp_off[instr.cond.n]}]")
            self._line(f"    cbz x0, {instr.false_label}")
            self._line(f"    b {instr.true_label}")

        elif isinstance(instr, IRJump):
            self._line(f"    b {instr.label}")

        elif isinstance(instr, IRLabel):
            self._line(f"{instr.name}:")

        elif isinstance(instr, IRCall):
            for i, arg in enumerate(instr.args):
                if i >= 8:
                    raise NotImplementedError("more than 8 arguments not supported")
                self._operand(f"x{i}", arg)
            self._line(f"    bl _{instr.func}")
            if instr.dest is not None:
                self._line(f"    str x0, [x29, #{self._temp_off[instr.dest.n]}]")

        elif isinstance(instr, IRReturn):
            if instr.value is not None:
                self._operand("x0", instr.value)
            else:
                self._line("    mov x0, #0")
            self._restore_frame()

        else:
            raise NotImplementedError(f"unhandled instruction: {type(instr).__name__}")


    # operand helpers

    def _operand(self, reg: str, op: Operand) -> None:
        if isinstance(op, Const):
            v = op.value
            if "." in v:
                raise NotImplementedError(
                    f"float literals not yet supported in ARM64 backend: '{v}'"
                )
            if v.startswith('"'):
                raise NotImplementedError("string literals not yet supported in ARM64 backend")
            self._line(f"    mov {reg}, #{v}")
        elif isinstance(op, Temp):
            self._line(f"    ldr {reg}, [x29, #{self._temp_off[op.n]}]")
        else:
            raise NotImplementedError(f"unknown operand type: {type(op)}")


    # output

    def _line(self, text: str) -> None:
        self._lines.append(text)


def generate_arm64(ir: list) -> str:
    """Translate an IR list to an ARM64 .s string ready for clang."""
    return ARM64Generator().generate(ir)
