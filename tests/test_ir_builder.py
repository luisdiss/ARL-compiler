import unittest
from compiler.lexer.lexer import lexer
from compiler.parser.parser import parser
from compiler.sa.semantic_analyser import semantic_analyser
from compiler.codegen.ir_builder import build_ir
from compiler.codegen.ir import (
    Temp, Const,
    IRBinOp, IRUnaryOp, IRLoad, IRStore, IRCompare,
    IRLabel, IRJump, IRCondJump, IRCall, IRReturn,
    IRFuncBegin, IRFuncEnd,
)
from compiler.lexer.token_utils import Token


def source_to_ir(src):
    tokens = lexer(src)
    tokens.append(Token("$", "$"))
    root = parser(tokens)
    semantic_analyser(root)
    return build_ir(root)


class TestIRConstants(unittest.TestCase):

    def test_number_emits_no_instruction(self):
        ir = source_to_ir("assign x = 5")
        self.assertEqual(len(ir), 1)
        self.assertIsInstance(ir[0], IRStore)

    def test_assign_integer(self):
        ir = source_to_ir("assign x = 5")
        self.assertEqual(ir[0].var, "x")
        self.assertIsInstance(ir[0].src, Const)
        self.assertEqual(ir[0].src.value, "5")

    def test_assign_float(self):
        ir = source_to_ir("assign x = 3.14")
        self.assertIsInstance(ir[0].src, Const)
        self.assertEqual(ir[0].src.value, "3.14")

    def test_bool_true(self):
        ir = source_to_ir("if true { assign x = 1 }")
        compares = [i for i in ir if isinstance(i, IRCompare)]
        self.assertEqual(compares[0].left, Const("1"))
        self.assertEqual(compares[0].op, "ne")

    def test_bool_false(self):
        ir = source_to_ir("if false { assign x = 1 }")
        compares = [i for i in ir if isinstance(i, IRCompare)]
        self.assertEqual(compares[0].left, Const("0"))


class TestIRExpressions(unittest.TestCase):

    def test_binary_op(self):
        ir = source_to_ir("assign x = 2 + 3")
        self.assertIsInstance(ir[0], IRBinOp)
        self.assertEqual(ir[0].op, "+")
        self.assertIsInstance(ir[0].left, Const)
        self.assertIsInstance(ir[0].right, Const)
        self.assertIsInstance(ir[1], IRStore)
        self.assertIsInstance(ir[1].src, Temp)

    def test_unary_op(self):
        ir = source_to_ir("assign x = -5")
        self.assertIsInstance(ir[0], IRUnaryOp)
        self.assertEqual(ir[0].op, "-")
        self.assertIsInstance(ir[0].src, Const)

    def test_nested_arithmetic_preserves_precedence(self):
        ir = source_to_ir("assign x = 1 + 2 * 3")
        binops = [i for i in ir if isinstance(i, IRBinOp)]
        self.assertEqual(len(binops), 2)
        self.assertEqual(binops[0].op, "*")
        self.assertEqual(binops[1].op, "+")

    def test_variable_reference_emits_load(self):
        ir = source_to_ir("assign x = 5\nassign y = x")
        self.assertIsInstance(ir[0], IRStore)
        self.assertIsInstance(ir[1], IRLoad)
        self.assertEqual(ir[1].var, "x")
        self.assertIsInstance(ir[2], IRStore)
        self.assertEqual(ir[2].var, "y")

    def test_temps_are_unique(self):
        ir = source_to_ir("assign x = 1 + 2 + 3")
        binops = [i for i in ir if isinstance(i, IRBinOp)]
        dest_ids = [b.dest.n for b in binops]
        self.assertEqual(len(dest_ids), len(set(dest_ids)))


class TestIRFunctions(unittest.TestCase):

    def test_func_begin_end(self):
        ir = source_to_ir("func f(a) { return a }")
        self.assertIsInstance(ir[0], IRFuncBegin)
        self.assertEqual(ir[0].name, "f")
        self.assertEqual(ir[0].params, ["a"])
        self.assertIsInstance(ir[-1], IRFuncEnd)
        self.assertEqual(ir[-1].name, "f")

    def test_return_const(self):
        ir = source_to_ir("func f() { return 1 }")
        returns = [i for i in ir if isinstance(i, IRReturn)]
        self.assertEqual(len(returns), 1)
        self.assertIsInstance(returns[0].value, Const)
        self.assertEqual(returns[0].value.value, "1")

    def test_return_expression(self):
        ir = source_to_ir("func f(a) { return a + 1 }")
        returns = [i for i in ir if isinstance(i, IRReturn)]
        self.assertIsInstance(returns[0].value, Temp)

    def test_call(self):
        ir = source_to_ir("func f(a) { return a }\ncall f(1)")
        calls = [i for i in ir if isinstance(i, IRCall)]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].func, "f")
        self.assertEqual(len(calls[0].args), 1)
        self.assertIsInstance(calls[0].args[0], Const)

    def test_call_multiple_args(self):
        ir = source_to_ir(
            "func f(a, b) { return a + b }\ncall f(1, 2)"
        )
        calls = [i for i in ir if isinstance(i, IRCall)]
        self.assertEqual(len(calls[0].args), 2)

    def test_call_result_stored(self):
        ir = source_to_ir(
            "func f(a) { return a }\nassign r = call f(1)"
        )
        calls = [i for i in ir if isinstance(i, IRCall)]
        stores = [i for i in ir if isinstance(i, IRStore)]
        self.assertIsNotNone(calls[0].dest)
        last_store = stores[-1]
        self.assertEqual(last_store.var, "r")
        self.assertEqual(last_store.src, calls[0].dest)


class TestIRConditionals(unittest.TestCase):

    def test_simple_comparison(self):
        ir = source_to_ir("if 1 lt 2 { assign x = 1 }")
        compares = [i for i in ir if isinstance(i, IRCompare)]
        self.assertEqual(len(compares), 1)
        self.assertEqual(compares[0].op, "lt")

    def test_chained_comparison_and(self):
        ir = source_to_ir("if 1 lt 2 gt 0 { assign x = 1 }")
        compares = [i for i in ir if isinstance(i, IRCompare)]
        self.assertEqual(len(compares), 2)
        ands = [i for i in ir if isinstance(i, IRBinOp) and i.op == "and"]
        self.assertEqual(len(ands), 1)

    def test_conditional_emits_labels_and_jumps(self):
        ir = source_to_ir("if 1 lt 2 { assign x = 1 }")
        labels = [i for i in ir if isinstance(i, IRLabel)]
        cond_jumps = [i for i in ir if isinstance(i, IRCondJump)]
        jumps = [i for i in ir if isinstance(i, IRJump)]
        self.assertEqual(len(cond_jumps), 1)
        self.assertGreaterEqual(len(labels), 2)
        self.assertGreaterEqual(len(jumps), 1)

    def test_else_branch(self):
        ir = source_to_ir(
            "if 1 lt 2 { assign x = 1 } else { assign y = 0 }"
        )
        labels = [i for i in ir if isinstance(i, IRLabel)]
        stores = [i for i in ir if isinstance(i, IRStore)]
        self.assertGreaterEqual(len(labels), 3)
        self.assertEqual(len(stores), 2)

    def test_conditional_body_store(self):
        ir = source_to_ir("if 1 lt 2 { assign x = 8 }")
        stores = [i for i in ir if isinstance(i, IRStore)]
        self.assertEqual(len(stores), 1)
        self.assertEqual(stores[0].var, "x")
        self.assertEqual(stores[0].src, Const("8"))


if __name__ == "__main__":
    unittest.main()
