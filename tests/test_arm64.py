import unittest
import subprocess
import tempfile
import os
from compiler.lexer.lexer import lexer
from compiler.parser.parser import parser
from compiler.sa.semantic_analyser import semantic_analyser
from compiler.codegen.ir_builder import build_ir
from compiler.codegen.arm64 import generate_arm64
from compiler.lexer.token_utils import Token


def source_to_asm(src):
    tokens = lexer(src)
    tokens.append(Token("$", "$"))
    root = parser(tokens)
    semantic_analyser(root)
    ir = build_ir(root)
    return generate_arm64(ir)


def compile_and_run(src):
    asm = source_to_asm(src)
    with tempfile.NamedTemporaryFile(suffix=".s", mode="w", delete=False) as f:
        f.write(asm)
        asm_path = f.name
    bin_path = asm_path.replace(".s", "")
    try:
        subprocess.run(
            ["clang", "-o", bin_path, asm_path],
            check=True, capture_output=True,
        )
        result = subprocess.run([bin_path], capture_output=True)
        return result.returncode
    finally:
        os.unlink(asm_path)
        if os.path.exists(bin_path):
            os.unlink(bin_path)


class TestARM64Structure(unittest.TestCase):

    def test_main_label(self):
        asm = source_to_asm("assign x = 5")
        self.assertIn("_main:", asm)
        self.assertIn(".global _main", asm)

    def test_function_label(self):
        asm = source_to_asm("func f(a) { return a }")
        self.assertIn("_f:", asm)

    def test_prologue(self):
        asm = source_to_asm("assign x = 5")
        self.assertIn("stp x29, x30, [sp, #-16]!", asm)
        self.assertIn("mov x29, sp", asm)

    def test_epilogue(self):
        asm = source_to_asm("assign x = 5")
        self.assertIn("ldp x29, x30, [sp], #16", asm)
        self.assertIn("ret", asm)

    def test_frame_alignment(self):
        asm = source_to_asm("assign x = 5")
        for line in asm.split("\n"):
            if "sub sp, sp, #" in line:
                size = int(line.strip().split("#")[1])
                self.assertEqual(size % 16, 0)

    def test_main_returns_zero(self):
        asm = source_to_asm("assign x = 5")
        lines = asm.split("\n")
        main_idx = next(i for i, l in enumerate(lines) if "_main:" in l)
        main_lines = lines[main_idx:]
        self.assertTrue(
            any("mov x0, #0" in l for l in main_lines)
        )

    def test_function_params_stored(self):
        asm = source_to_asm("func f(a, b) { return a + b }")
        lines = asm.split("\n")
        func_idx = next(i for i, l in enumerate(lines) if "_f:" in l)
        func_lines = lines[func_idx:]
        param_stores = [l for l in func_lines if "str x0" in l or "str x1" in l]
        self.assertGreaterEqual(len(param_stores), 2)


class TestARM64Errors(unittest.TestCase):

    def test_float_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            source_to_asm("assign x = 1.5")

    def test_string_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            source_to_asm('assign x = "hello"')


class TestARM64EndToEnd(unittest.TestCase):
    """Compile, assemble, link, and run ARM64 binaries. Exit code 0 = no crash."""

    @classmethod
    def setUpClass(cls):
        try:
            subprocess.run(["clang", "--version"], capture_output=True, check=True)
            cls.has_clang = True
        except (FileNotFoundError, subprocess.CalledProcessError):
            cls.has_clang = False

    def setUp(self):
        if not self.has_clang:
            self.skipTest("clang not available")

    def test_assign(self):
        self.assertEqual(compile_and_run("assign x = 5"), 0)

    def test_binary_ops(self):
        self.assertEqual(compile_and_run("assign x = 2 + 3"), 0)
        self.assertEqual(compile_and_run("assign x = 10 - 4"), 0)
        self.assertEqual(compile_and_run("assign x = 3 * 7"), 0)
        self.assertEqual(compile_and_run("assign x = 10 / 2"), 0)

    def test_unary_neg(self):
        self.assertEqual(compile_and_run("assign x = -5"), 0)

    def test_nested_arithmetic(self):
        self.assertEqual(compile_and_run("assign x = 1 + 2 * 3"), 0)

    def test_function_call(self):
        src = "func add(a, b) { return a + b }\nassign r = call add(2, 3)"
        self.assertEqual(compile_and_run(src), 0)

    def test_function_with_expression(self):
        src = "func f(a) { return a + 2 * 3 }\nassign r = call f(1)"
        self.assertEqual(compile_and_run(src), 0)

    def test_conditional_true(self):
        self.assertEqual(compile_and_run("if 1 lt 2 { assign x = 1 }"), 0)

    def test_conditional_false(self):
        self.assertEqual(compile_and_run("if 2 lt 1 { assign x = 1 }"), 0)

    def test_conditional_else(self):
        src = "assign x = 10\nif x gt 5 { assign y = 1 } else { assign z = 0 }"
        self.assertEqual(compile_and_run(src), 0)

    def test_chained_comparison(self):
        self.assertEqual(
            compile_and_run("if 1 lt 2 gt 0 { assign x = 1 }"), 0
        )

    def test_multiple_assigns(self):
        src = "assign a = 1\nassign b = 2\nassign c = 3"
        self.assertEqual(compile_and_run(src), 0)

    def test_variable_in_expression(self):
        src = "assign x = 5\nassign y = x"
        self.assertEqual(compile_and_run(src), 0)


if __name__ == "__main__":
    unittest.main()
