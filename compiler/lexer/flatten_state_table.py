from compiler.lexer.raw_state_table import raw_state_table, transiton_classes
import pprint

"""
Utility script that expands transition classes into explicit
character-to-state mappings and writes the resulting flattened
state table to a Python file.
"""

from compiler.lexer.raw_state_table import raw_state_table, transiton_classes
import pprint


def flatten_state_table(state_table: dict) -> dict:
    """
    Expand transition classes into direct character transitions.

    Each transition class in `transiton_classes` is replaced with
    individual character entries so the resulting state table can
    perform O(1) character lookups during lexing.

    Args:
        state_table: State machine definition containing transition
            class references.

    Returns:
        A new state table with all transition classes expanded into
        explicit character mappings.
    """
    new_state_table: dict = {}

    for state, state_info in state_table.items():
        new_transitions: dict = {}

        for trans_class, to_state in state_info.get("transitions", {}).items():
            for char in transiton_classes[trans_class]:
                new_transitions[char] = to_state

        new_state_table[state] = {
            **state_info,
            "transitions": new_transitions,
        }

    return new_state_table


flattened_state_table = flatten_state_table(raw_state_table)

with open("compiler/lexer/flattened_state_table.py", "w") as f:
    f.write("flattened_state_table = ")
    f.write(pprint.pformat(flattened_state_table))
    f.write("\n")