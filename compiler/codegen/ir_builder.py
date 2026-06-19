from __future__ import annotations
from typing import Any, Optional

from compiler.parser.ast_nodes import (
    PNode, FuncDefNode, FuncBodyNode, ReturnNode,
    ParamsNode, ParamNode, KeyWordParamNode,
    AssignNode, ExprNode, BinaryOpNode, UnaryOpNode,
    ConditionalNode, ConditionalBodyNode,
    ComparisonOpNode, ComparisonsNode,
    BoolNode, CallNode, ArgsNode, ArgNode, KeyWordArgNode,
    NumberNode, ExprIDNode, DeclIDNode, StringNode,
)
from compiler.codegen.ir import (
    Temp, Const, Operand,
    IRBinOp, IRUnaryOp, IRLoad, IRStore, IRCompare,
    IRLabel, IRJump, IRCondJump, IRCall, IRReturn,
    IRFuncBegin, IRFuncEnd,
)


class IRBuilderVisitor:
    """
    Walks a semantically-analysed AST and emits a flat list of IR instructions.

    Expression visitors return the Operand (Temp or Const) that holds their
    result.  Statement visitors return None and emit instructions as a side
    effect.
    """

    def __init__(self) -> None:
        self.instructions: list = []
        self._temp_n: int = 0
        self._label_n: int = 0

    # helpers

    def _fresh_temp(self) -> Temp:
        t = Temp(self._temp_n)
        self._temp_n += 1
        return t

    def _fresh_label(self, prefix: str) -> str:
        label = f"{prefix}_{self._label_n}"
        self._label_n += 1
        return label

    def _emit(self, instr: Any) -> None:
        self.instructions.append(instr)


    # dispatch

    def visit(self, node: Any) -> Optional[Operand]:
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Any) -> None:
        for child in node.children_api():
            self.visit(child)


    # top-level structure

    def visit_PNode(self, node: PNode) -> None:
        for child in node.children:
            self.visit(child)

    def visit_FuncDefNode(self, node: FuncDefNode) -> None:
        params = [p.id.value for p in node.params.children]
        self._emit(IRFuncBegin(node.id.value, params))
        self.visit(node.funcbody)
        self._emit(IRFuncEnd(node.id.value))

    # FuncBodyNode uses the same right-recursive structure as ConditionalBodyNode:
    # children may be [stmt, FuncBodyNode([...])] for multi-statement bodies.
    def visit_FuncBodyNode(self, node: FuncBodyNode) -> None:
        for child in node.children:
            self.visit(child)


    # statements

    def visit_AssignNode(self, node: AssignNode) -> None:
        src = self.visit(node.expr)
        self._emit(IRStore(node.id.value, src))

    def visit_ReturnNode(self, node: ReturnNode) -> None:
        val = self.visit(node.expr)
        self._emit(IRReturn(val))

    def visit_ConditionalNode(self, node: ConditionalNode) -> None:
        n = self._label_n
        self._label_n += 1
        if_label = f"if_{n}_body"
        else_label = f"if_{n}_else"
        end_label = f"if_{n}_end"

        cond = self._lower_condition(node.comparison)

        if node._else is not None:
            self._emit(IRCondJump(cond, if_label, else_label))
        else:
            self._emit(IRCondJump(cond, if_label, end_label))

        self._emit(IRLabel(if_label))
        if node._if is not None:
            self.visit(node._if)
        self._emit(IRJump(end_label))

        if node._else is not None:
            self._emit(IRLabel(else_label))
            self.visit(node._else)
            self._emit(IRJump(end_label))

        self._emit(IRLabel(end_label))

    # ConditionalBodyNode shares the right recursive nesting pattern with
    # FuncBodyNode children may include nested ConditionalBodyNode objects.
    def visit_ConditionalBodyNode(self, node: ConditionalBodyNode) -> None:
        for child in node.children:
            self.visit(child)


    # expressions (all return Operand)

    def visit_ExprNode(self, node: ExprNode) -> Optional[Operand]:
        return self.visit(node.entry)

    def visit_NumberNode(self, node: NumberNode) -> Const:
        # Return the constant inline; no instruction emitted.
        return Const(node.value)

    def visit_StringNode(self, node: StringNode) -> Const:
        return Const(node.value)

    def visit_BoolNode(self, node: BoolNode) -> Const:
        return Const("1" if node.value == "true" else "0")

    def visit_ExprIDNode(self, node: ExprIDNode) -> Temp:
        dest = self._fresh_temp()
        self._emit(IRLoad(dest, node.value))
        return dest

    def visit_BinaryOpNode(self, node: BinaryOpNode) -> Temp:
        left = self.visit(node.left)
        right = self.visit(node.right)
        dest = self._fresh_temp()
        self._emit(IRBinOp(dest, left, node.op, right))
        return dest

    def visit_UnaryOpNode(self, node: UnaryOpNode) -> Temp:
        src = self.visit(node.value)
        dest = self._fresh_temp()
        self._emit(IRUnaryOp(dest, node.op, src))
        return dest

    def visit_CallNode(self, node: CallNode) -> Temp:
        args: list[Operand] = []
        for arg_node in node.args.children:
            operand = self.visit(arg_node)
            if operand is not None:
                args.append(operand)
        dest = self._fresh_temp()
        self._emit(IRCall(dest, node.id.value, args))
        return dest

    def visit_ArgNode(self, node: ArgNode) -> Optional[Operand]:
        return self.visit(node.expr)

    def visit_KeyWordArgNode(self, node: KeyWordArgNode) -> Optional[Operand]:
        return self.visit(node.expr)


    # condition lowering for if statements

    def _lower_condition(self, node: Any) -> Temp:
        """
        Reduce any condition expression to a boolean Temp (1=true, 0=false).

        Handles BoolNode, ComparisonsNode (chained with AND), and bare ExprNode.
        """
        if isinstance(node, BoolNode):
            val = Const("1" if node.value == "true" else "0")
            dest = self._fresh_temp()
            # t = val != 0  →  always 1 for true, always 0 for false
            self._emit(IRCompare(dest, val, "ne", Const("0")))
            return dest

        if isinstance(node, ComparisonsNode):
            result = self._lower_single_cmp(node.children[0])
            for cmp_node in node.children[1:]:
                right = self._lower_single_cmp(cmp_node)
                combined = self._fresh_temp()
                self._emit(IRBinOp(combined, result, "and", right))
                result = combined
            return result

        # Bare expression used as condition (e.g. `if 1 { }`).
        val = self.visit(node)
        if isinstance(val, Temp):
            return val
        dest = self._fresh_temp()
        self._emit(IRCompare(dest, val, "ne", Const("0")))
        return dest

    def _lower_single_cmp(self, node: ComparisonOpNode) -> Temp:
        left = self.visit(node.left)
        right = self.visit(node.right)
        dest = self._fresh_temp()
        self._emit(IRCompare(dest, left, node.op, right))
        return dest


def build_ir(root: Any) -> list:
    """Run the IR builder over a typed AST and return the instruction list."""
    builder = IRBuilderVisitor()
    builder.visit(root)
    return builder.instructions
