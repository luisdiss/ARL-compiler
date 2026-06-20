from compiler.lexer.lexer import lexer
from compiler.parser.parser import parser
from compiler.sa.semantic_analyser import semantic_analyser
from compiler.codegen.ir_builder import build_ir
from compiler.codegen.arm64 import generate_arm64
from compiler.lexer.token_utils import Token


def compiler(program: str) -> str:
    tokens = lexer(program)
    tokens.append(Token("$", "$"))
    root = parser(tokens)
    semantic_analyser(root)
    ir = build_ir(root)
    return generate_arm64(ir)
