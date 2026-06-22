from lark import Lark

grammar = """
    start: statement*

    statement: func_def | assign | conditional | expr

    func_def: "func" NAME "(" params ")" "{" func_entry* "}"

    func_entry: "return" expr | func_def | assign | conditional | expr

    params: param_list ("," keyword_param)* | keyword_param ("," keyword_param)* |
    param_list: NAME ("," NAME)*
    keyword_param: assign

    assign: "assign" NAME "=" expr

    expr: term (add_op term)*

    term: factor (mult_op factor)*

    factor: unary_op factor | "(" expr ")" | atom

    unary_op: "+" | "-"

    add_op: "+" | "-"

    mult_op: "*" | "/"

    atom: NUMBER | STRING | call | NAME

    conditional: "if" comparison "{" conditional_entry* "}" ("else" "{" conditional_entry* "}")?

    comparison: expr (comp_op expr)* | bool
    comp_op: "gt" | "lt" | "ge" | "le" | "eq" | "ne"
    bool: "true" | "false"

    conditional_entry: assign | expr

    call: "call" NAME "(" args ")"

    args: arg_list ("," keyword_arg)* | keyword_arg ("," keyword_arg)* |
    arg_list: expr ("," expr)*
    keyword_arg: assign

    %import common.CNAME -> NAME
    %import common.NUMBER
    %import common.ESCAPED_STRING -> STRING
    %import common.WS
    %ignore WS
"""

parser = Lark(grammar, parser="lalr")