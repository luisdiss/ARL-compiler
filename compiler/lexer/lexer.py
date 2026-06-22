from compiler.lexer.token_utils import Token
from compiler.lexer.flattened_state_table import flattened_state_table as state_table
from compiler.errors import LexError, SourcePos


def lexer(s: str) -> list[Token]:
    """
    Tokenise the input string using the configured DFA state table.

    Walks the input character by character, following transitions defined
    in ``state_table``. Whenever an accepting state is reached the
    corresponding token type is remembered. When no further transition is
    possible the most recently accepted token is emitted via Token.from_dfa
    and lexing resumes from the start state.

    Args:
        s: Input source text to tokenise.

    Returns:
        A list of Token objects carrying type, value, and source position.

    Raises:
        LexError: If an unexpected character is encountered and no valid
            token has been accepted.
    """
    state: str = "S1"
    i: int = 0
    line: int = 1
    col: int = 1
    token_start_line: int = 1
    token_start_col: int = 1
    tokens: list[Token] = []
    accepted_token_type: str = ""
    accepted_line: int = 1
    accepted_col: int = 1
    buffer: str = ""

    while i < len(s):
        char = s[i]
        transitions = state_table[state]["transitions"]
        next_state = transitions.get(char)

        if next_state:
            buffer += char
            i += 1
            if char == "\n":
                line += 1
                col = 1
            else:
                col += 1
            state = next_state

            if (a := state_table[state].get("accepting_token_type")) is not None:
                accepted_token_type = a
                accepted_line = token_start_line
                accepted_col = token_start_col
        else:
            if accepted_token_type:
                tok = Token.from_dfa(accepted_token_type, buffer, accepted_line, accepted_col)
                if tok:
                    tokens.append(tok)
                state, accepted_token_type, buffer = "S1", "", ""
                token_start_line, token_start_col = line, col
            else:
                raise LexError(
                    f"Unexpected character '{char}'",
                    SourcePos(line, col),
                )
    else:
        if accepted_token_type:
            tok = Token.from_dfa(accepted_token_type, buffer, accepted_line, accepted_col)
            if tok:
                tokens.append(tok)
        else:
            #new ------------------------
            if buffer:
                raise LexError(
                    f"Unexpected token",
                    SourcePos(line, col),
                )
            #----------------------------

    return tokens
