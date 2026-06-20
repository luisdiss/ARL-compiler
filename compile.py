import sys
import os
from compiler.errors import CompilerError, CompilationFailed
from compiler.compiler import compiler

filename = sys.argv[1]
out_filename = os.path.splitext(filename)[0] + ".s"

with open(filename, 'r') as file:
    content = file.read()

try:
    compiler()

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
