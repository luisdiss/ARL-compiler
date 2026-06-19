from compiler.parser.ast_nodes import KeyWordParamNode, ArgNode, KeyWordArgNode, FuncDefNode
from compiler.errors import SemanticError
from enum import Enum, auto
from typing import Dict, List, Optional, Any


class SA:
    """
    Semantic Analysis state object persisting for the lifetime of analysis.

    Maintains the scope hierarchy, node-to-scope mappings, and the active
    scope stack during traversal.

    Attributes:
        scope_tree: Root of the current scope hierarchy.
        node_to_scope: Mapping from AST nodes to their defining scopes.
        scope_stack: Stack of active scopes for hierarchical traversal.
    """

    def __init__(self) -> None:
        dummy_scope: Scope = Scope()
        self.scope_tree: Scope = dummy_scope
        self.node_to_scope: Dict[Any, Scope] = {}
        self.scope_stack: List[Scope] = [dummy_scope]
        self.errors: List[SemanticError] = []


class Scope:
    """
    Represents a lexical scope within the program.

    Contains symbol definitions, hierarchical links, and type constraint
    information for resolution within this scope.

    Attributes:
        symbol_table: Mapping of identifier names to Symbol objects.
        parent: Reference to the enclosing parent scope.
        constraints: List of type constraints applicable to this scope.
        substitution: Mapping for type variable substitutions.
        func_id_symbol: Symbol reference for the function defining this scope.
    """

    def __init__(self) -> None:
        self.symbol_table: Dict[str, Symbol] = {}
        self.parent: Optional[Scope] = None
        self.constraints: List[Any] = []
        self.substitution: Dict[Any, Any] = {}
        self.func_id_symbol: Optional[Symbol] = None


class Symbol:
    """
    Represents a unique identifier symbol owned by ID nodes.

    Stores type information and function-specific metadata for semantic
    resolution.

    Attributes:
        id: The identifier string name.
        type: The resolved type of the symbol.
        funcdef_node: Reference to the function definition node (if applicable).
        params: List of parameter symbols (if applicable).
        kwparams: Dictionary of keyword parameters (if applicable).
        param_map: Mapping of parameter names to symbols (if applicable).
        analysed: Flag indicating whether semantic analysis is complete.
    """

    def __init__(self, id: str) -> None:
        self.id: str = id
        self.type: Optional[Types] = None
        self.funcdef_node: Optional[Any] = None
        self.params: Optional[List[Symbol]] = None
        self.kwparams: Optional[Dict[str, Symbol]] = None
        self.param_map: Optional[Dict[str, Symbol]] = None
        self.analysed: bool = False


class Types(Enum):
    """Enumeration of primitive types supported by the semantic analyser."""

    number = auto()
    string = auto()
    bool = auto()


class ScopeDeclBaseVisitor:
    """
    Base visitor class for traversing the AST and managing scope context.

    Implements the Visitor pattern to associate AST nodes with their
    corresponding scopes and delegate specific node handling to subclasses.

    Attributes:
        SA: Reference to the global Semantic Analysis state object.
    """

    def __init__(self, sa: SA) -> None:
        self.sa: SA = sa

    def visit(self, node: Any) -> None:
        """
        Visits a node, records its scope, and dispatches to specific handler.

        Args:
            node: The AST node to visit.
        """
        self.sa.node_to_scope[node] = self.sa.scope_stack[-1]
        methodname: str = "visit_" + node.__class__.__name__
        visit_method = getattr(self, methodname, None)
        if visit_method:
            visit_method(node)
        else:
            self.generic_visitor(node)

    def generic_visitor(self, node: Any) -> None:
        """
        Default traversal logic for nodes without specific handlers.

        Recursively visits all children of the node.

        Args:
            node: The AST node to traverse.
        """
        if node:
            for child in node.children_api():
                self.visit(child)


class ScopeDeclVisitor(ScopeDeclBaseVisitor):
    """
    Concrete visitor implementation for scope declaration and resolution.

    Handles function definitions, parameter scoping, and identifier
    resolution/declaration logic.
    """

    def __init__(self, SA: SA) -> None:
        super().__init__(SA)

    def visit_PNode(self, node: Any) -> None:
        """
        Visits a Program node, creating a new scope for its body.

        Args:
            node: The Program AST node.
        """
        self.enter_scope(node)
        for child in node.children:
            self.visit(child)
        self.exit_scope()

    def visit_FuncDefNode(self, node: Any) -> None:
        """
        Visits a Function Definition node, handling parameters and body scope.

        Processes parameter expressions, enters a new scope for the function
        body, declares parameters, and visits the function body.

        Args:
            node: The Function Definition AST node.
        """
        self.visit(node.id)
        for param in node.params.children:
            if isinstance(param, KeyWordParamNode):
                self.visit(param.expr)

        self.enter_scope(node)
        for param in node.params.children:
            self.visit(param.id)
        self.visit(node.funcbody)
        self.exit_scope()

    def visit_ExprIDNode(self, node: Any) -> None:
        """
        Visits an Expression Identifier node, resolving it to a symbol.

        Args:
            node: The Expression Identifier AST node.
        """
        self.resolve_id(node)

    def visit_DeclIDNode(self, node: Any) -> None:
        """
        Visits a Declaration Identifier node, declaring a new symbol.

        Args:
            node: The Declaration Identifier AST node.
        """
        self.check_decl(node)

    def get_curr_scope(self, node: Any) -> Scope:
        """
        Retrieves the scope associated with the given node.

        Args:
            node: The AST node.

        Returns:
            The Scope object associated with the node.
        """
        return self.sa.node_to_scope[node]

    def enter_scope(self, node: Any) -> None:
        """
        Creates and pushes a new scope onto the stack.

        Establishes parent linkage and associates function symbols if
        entering a function definition scope.

        Args:
            node: The AST node triggering the new scope.
        """
        scope: Scope = Scope()
        scope.parent = self.sa.scope_tree
        self.sa.scope_tree = scope
        self.sa.scope_stack.append(scope)
        if isinstance(node, FuncDefNode):
            scope.func_id_symbol = node.id.symbol

    def exit_scope(self) -> None:
        """Pops the current scope from the stack."""
        self.sa.scope_stack.pop()

    def check_decl(self, node: Any) -> None:
        """
        Checks for duplicate declarations and creates a new symbol if valid.

        Args:
            node: The Declaration Identifier AST node.
        """
        curr_scope: Scope = self.get_curr_scope(node)
        id_val: str = node.value
        if id_val not in curr_scope.symbol_table:
            new_symbol: Symbol = Symbol(id_val)
            curr_scope.symbol_table[id_val] = new_symbol
            node.symbol = new_symbol
        else:
            self.sa.errors.append(SemanticError(f"'{id_val}' is already defined in this scope"))

    def resolve_id(self, node: Any) -> None:
        """
        Resolves an identifier by searching up the scope chain.

        Searches from the current scope to the global scope for the
        identifier definition.

        Args:
            node: The Expression Identifier AST node.
        """
        scope: Optional[Scope] = self.sa.node_to_scope[node]
        while scope:
            if node.value in scope.symbol_table:
                node.symbol = scope.symbol_table[node.value]
                break
            scope = scope.parent
        else:
            self.sa.errors.append(SemanticError(f"'{node.value}' is not defined"))


class InferenceBaseVisitor:
    """
    Base visitor class responsible for inferring types across the AST.

    Implements the core Visitor pattern to traverse nodes and delegate
    specific type inference logic to concrete subclasses.

    Attributes:
        SA: Reference to the global Semantic Analysis state object.
    """

    def __init__(self, sa: Any) -> None:
        self.sa: Any = sa

    def visit(self, node: Any) -> Optional[Enum]:
        """
        Dispatches the node to its specific visitor method.

        Dynamically resolves the handler method based on the node's class
        name. Falls back to generic traversal if no specific handler exists.

        Args:
            node: The AST node to visit.

        Returns:
            The inferred type of the node, if applicable.
        """
        methodname: str = "visit_" + node.__class__.__name__
        visit_method = getattr(self, methodname, self.generic_visit)
        return visit_method(node)

    def generic_visit(self, node: Any) -> None:
        """
        Default traversal logic for nodes without specific type inference.

        Recursively visits all children to ensure full tree coverage.

        Args:
            node: The AST node to traverse.
        """
        if node:
            for child in node.children_api():
                self.visit(child)


class InferenceVisitor(InferenceBaseVisitor):
    """
    Concrete visitor implementation for semantic type inference.

    Handles function definitions, call resolution, argument binding,
    and expression type propagation.
    """

    def __init__(self, SA: Any) -> None:
        super().__init__(SA)

    def visit_FuncDefNode(self, node: Any) -> None:
        """
        Processes a function definition to initialise symbol metadata.

        Maps parameters to symbols, stores parameter lists, and links
        the symbol to its definition node.

        Args:
            node: The Function Definition AST node.
        """
        node.id.symbol.param_map = {
            param.id.value: param for param in node.params.children
        }
        node.id.symbol.params = [
            paramnode for paramnode in node.params.children
        ]
        node.id.symbol.funcdef_node = node

    def visit_CallNode(self, node: Any) -> Optional[Enum]:
        """
        Visits a function call node to infer or verify argument types.

        Binds arguments to parameters, infers parameter types on first
        analysis, and checks type consistency on subsequent calls.

        Args:
            node: The Call AST node.

        Returns:
            The return type of the called function.
        """
        symbol: Any = node.id.symbol
        param_arg_map: Dict[Any, Any] = self.bind_call_arguments(node, symbol)

        if not symbol.analysed:
            self.infer_parameter_types(symbol, param_arg_map)
            self.visit(symbol.funcdef_node.funcbody)
            symbol.analysed = True
        else:
            self.check_argument_types(symbol, param_arg_map)

        return symbol.type

    def visit_ReturnNode(self, node: Any) -> None:
        """
        Visits a return statement to infer the function's return type.

        Traverses up the scope chain to locate the defining function
        symbol and assigns the evaluated expression type to it.

        Args:
            node: The Return AST node.
        """
        scope: Optional[Any] = self.sa.node_to_scope[node]
        func_scope: Optional[Any] = scope

        while func_scope and not hasattr(func_scope, "func_id_symbol"):
            func_scope = func_scope.parent

        if func_scope:
            func_id_symbol: Any = func_scope.func_id_symbol
            func_id_symbol.type = self.visit(node.expr)

    def visit_ArgNode(self, node: Any) -> Optional[Enum]:
        """
        Visits an argument node to propagate type information.

        Args:
            node: The Argument AST node.

        Returns:
            The inferred type of the argument expression.
        """
        return self.visit(node.expr)

    def visit_AssignNode(self, node: Any) -> Optional[Enum]:
        """
        Visits an assignment node to infer the variable's type.

        Args:
            node: The Assignment AST node.

        Returns:
            The inferred type of the assigned expression.
        """
        node.id.symbol.type = self.visit(node.expr)
        return node.id.symbol.type

    def visit_ExprNode(self, node: Any) -> Optional[Enum]:
        """
        Visits a generic expression node.

        Args:
            node: The Expression AST node.

        Returns:
            The type of the entry expression.
        """
        return self.visit(node.entry)

    def visit_BinaryOpNode(self, node: Any) -> Optional[Enum]:
        """
        Visits a binary operation node to validate operand types.

        Currently enforces that both operands are numbers for arithmetic
        operations.

        Args:
            node: The Binary Operation AST node.

        Returns:
            The resulting type of the operation, or None on error.
        """
        left_t: Optional[Enum] = self.visit(node.left)
        right_t: Optional[Enum] = self.visit(node.right)

        if left_t == right_t and left_t == Types.number:
            return Types.number
        else:
            self.sa.errors.append(SemanticError(
                f"both operands of '{node.op}' must be of type number, "
                f"got {left_t} and {right_t}"
            ))
            return None

    def visit_ComparisonOpNode(self, node: Any) -> Optional[Enum]:
        """
        Visits a comparison operation node to validate operand types.

        Args:
            node: The Comparison Operation AST node.

        Returns:
            Types.number when operands are valid, None on error.
        """
        left_t: Optional[Enum] = self.visit(node.left)
        right_t: Optional[Enum] = self.visit(node.right)

        if left_t == right_t and left_t == Types.number:
            return Types.number
        else:
            self.sa.errors.append(SemanticError(
                f"both operands of '{node.op}' must be of type number, "
                f"got {left_t} and {right_t}"
            ))
            return None

    def visit_UnaryOpNode(self, node: Any) -> Optional[Enum]:
        """
        Visits a unary operation node.

        Args:
            node: The Unary Operation AST node.

        Returns:
            The type of the operand.
        """
        return self.visit(node.value)

    def visit_ExprIDNode(self, node: Any) -> Optional[Enum]:
        """
        Visits an identifier expression node.

        Args:
            node: The Identifier Expression AST node.

        Returns:
            The type associated with the identifier's symbol.
        """
        return node.symbol.type

    def visit_NumberNode(self, _node: Any) -> Types:
        """Visits a numeric literal node."""
        return Types.number

    def visit_StringNode(self, _node: Any) -> Types:
        """Visits a string literal node."""
        return Types.string

    def visit_BoolNode(self, _node: Any) -> Types:
        """Visits a boolean literal node."""
        return Types.bool

    def infer_parameter_types(
        self, symbol: Any, param_arg_map: Dict[Any, Any]
    ) -> None:
        """
        Infers types for function parameters based on passed arguments.

        Handles default values and validates type consistency between
        defaults and provided arguments.

        Args:
            symbol: The function symbol containing parameter metadata.
            param_arg_map: Mapping of parameters to their bound argument nodes.
        """
        for param in symbol.params:
            default_type: Optional[Enum] = None
            if param.has_default:
                default_type = self.visit(param.expr)

            arg_node: Any = param_arg_map[param]
            using_default: bool = (
                param.has_default and arg_node is param.expr
            )

            if using_default:
                param.id.symbol.type = default_type
            else:
                arg_type: Optional[Enum] = self.visit(arg_node.expr)
                if param.has_default:
                    if arg_type != default_type:
                        self.sa.errors.append(SemanticError(
                            f"type mismatch for parameter '{param.id.value}': "
                            f"default is {default_type}, argument is {arg_type}"
                        ))
                        return

                param.id.symbol.type = arg_type

    def check_argument_types(
        self, symbol: Any, param_arg_map: Dict[Any, Any]
    ) -> None:
        """
        Verifies that provided arguments match inferred parameter types.

        Args:
            symbol: The function symbol containing parameter metadata.
            param_arg_map: Mapping of parameters to their bound argument nodes.
        """
        for param in symbol.params:
            param_id: Any = param.id
            arg_node: Any = param_arg_map[param]
            arg_type: Optional[Enum] = self.visit(arg_node.expr)

            if arg_type != param_id.symbol.type:
                self.sa.errors.append(SemanticError(
                    f"type mismatch for parameter '{param_id.value}': "
                    f"expected {param_id.symbol.type}, got {arg_type}"
                ))

    def bind_call_arguments(
        self, call_node: Any, symbol: Any
    ) -> Dict[Any, Any]:
        """
        Binds call arguments to their corresponding parameters.

        Handles positional and keyword arguments, detects duplicates,
        and ensures all required parameters are satisfied.

        Args:
            call_node: The Call AST node.
            symbol: The function symbol containing parameter metadata.

        Returns:
            A mapping of parameters to their bound argument nodes.
        """
        args: List[Any] = [
            arg
            for arg in call_node.args.children
            if isinstance(arg, ArgNode)
        ]
        kwargs: List[Any] = [
            arg
            for arg in call_node.args.children
            if isinstance(arg, KeyWordArgNode)
        ]
        params: List[Any] = symbol.params
        param_map: Dict[str, Any] = symbol.param_map
        param_arg_map: Dict[Any, Any] = {}
        total_params: int = len(params)

        if len(args) + len(kwargs) > total_params:
            self.sa.errors.append(SemanticError(
                f"too many arguments in call to '{call_node.id.value}': "
                f"expected {total_params}, got {len(args) + len(kwargs)}"
            ))

        # Bind positional args
        for i, arg in enumerate(args):
            param: Any = params[i]
            param_arg_map[param] = arg

        # Bind keyword args
        for kwarg in kwargs:
            name: str = kwarg.id.value
            if name not in param_map:
                self.sa.errors.append(SemanticError(
                    f"unknown parameter '{name}' in call to '{call_node.id.value}'"
                ))
                continue

            param: Any = param_map[name]
            if param in param_arg_map:
                self.sa.errors.append(SemanticError(
                    f"parameter '{name}' is already bound"
                ))
                continue

            param_arg_map[param] = kwarg

        # Check for missing positional args
        for param in params:
            if param not in param_arg_map:
                if param.has_default:
                    param_arg_map[param] = param.expr
                else:
                    self.sa.errors.append(SemanticError(
                        f"missing required argument for parameter '{param.id.value}'"
                    ))

        return param_arg_map  