from compiler.lexer.lexer import lexer
from compiler.parser.parser import parser
from compiler.parser.parser_utils import ASTPrinter
from compiler.sa.semantic_analyser import semantic_analyser
from compiler.codegen.ir_builder import build_ir
from compiler.codegen.arm64 import generate_arm64
from compiler.lexer.token_utils import Token

def compiler() -> str:
    tokens = lexer(content)
    root = parser(tokens.append(Token("$", "$")))
    semantic_analyser(root)
    ir = build_ir(root)
    return generate_arm64(ir)
