from compiler.sa.sa_utils import SA, ScopeDeclVisitor, InferenceVisitor
from compiler.errors import CompilationFailed
from typing import Any


def semantic_analyser(ast_root: Any) -> SA:
    """
    Executes the complete semantic analysis pipeline on the provided AST.

    Runs scope declaration then type inference. Raises CompilationFailed
    if any semantic errors were collected during either pass.

    Args:
        ast_root: The root node of the Abstract Syntax Tree to analyse.

    Returns:
        The populated SA state object.

    Raises:
        CompilationFailed: If any semantic errors were encountered.
    """
    sa = SA()

    ScopeDeclVisitor(sa).visit(ast_root)
    InferenceVisitor(sa).visit(ast_root)

    if sa.errors:
        raise CompilationFailed(sa.errors)

    return sa
