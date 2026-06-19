from compiler.lexer.lexer import lexer
from compiler.parser.parser import parser
from compiler.parser.parser_utils import ASTPrinter
from compiler.sa.semantic_analyser import semantic_analyser
from compiler.codegen.ir_builder import build_ir
from compiler.codegen.arm64 import generate_arm64
from compiler.lexer.token_utils import Token
from compiler.errors import CompilerError, CompilationFailed
import sys
import os

filename = sys.argv[1]
out_filename = os.path.splitext(filename)[0] + ".s"

with open(filename, 'r') as file:
    content = file.read()

try:
    tokens = lexer(content)
    print(f'Tokens:\n\n{tokens}\n')

    tokens.append(Token("$", "$"))
    root = parser(tokens)

    semantic_analyser(root)

    print('Syntax tree:\n')
    ASTPrinter().visit(root)

    ir = build_ir(root)
    print(ir)
    asm = generate_arm64(ir)
    print(asm)

    with open(out_filename, 'w') as f:
        f.write(asm)
    print(f'\nAssembly written to {out_filename}')

except CompilationFailed as e:
    for error in e.errors:
        print(f"error: {error}", file=sys.stderr)
    sys.exit(1)
except CompilerError as e:
    print(f"error: {e}", file=sys.stderr)
    sys.exit(1)
except NotImplementedError as e:
    print(f"error: not yet supported: {e}", file=sys.stderr)
    sys.exit(1)