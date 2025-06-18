"""
Linting of CFEngine related files.

Currently implemented for:
- *.cf (policy files)
- cfbs.json (CFEngine Build project files)
- *.json (basic JSON syntax checking)

Usage:
$ cfengine lint
"""

import os
import json
import tree_sitter_cfengine as tscfengine
from tree_sitter import Language, Parser
from cfbs.validate import validate_config
from cfbs.cfbs_config import CFBSConfig


def lint_cfbs_json(filename) -> int:
    assert os.path.isfile(filename)
    assert filename.endswith("cfbs.json")

    config = CFBSConfig.get_instance(filename=filename, non_interactive=True)
    r = validate_config(config)

    if r == 0:
        print(f"PASS: {filename}")
        return 0
    print(f"FAIL: {filename}")
    return r


def lint_json(filename) -> int:
    assert os.path.isfile(filename)

    with open(filename, "r") as f:
        data = f.read()

    try:
        data = json.loads(data)
    except:
        print(f"FAIL: {filename} (invalid JSON)")
        return 1
    print(f"PASS: {filename}")
    return 0


def _highlight_range(node, lines):
    line = node.range.start_point[0] + 1
    column = node.range.start_point[1]

    length = len(lines[line - 1]) - column
    if node.range.start_point[0] == node.range.end_point[0]:
        # Starts and ends on same line:
        length = node.range.end_point[1] - node.range.start_point[1]
    assert length >= 1
    print("")
    if line >= 2:
        print(lines[line - 2])
    print(lines[line - 1])
    marker = "^"
    if length > 2:
        marker += "-" * (length - 2)
    if length > 1:
        marker += "^"
    print(" " * column + marker)


def _text(node):
    return node.text.decode()


def _walk(filename, lines, node) -> int:
    line = node.range.start_point[0] + 1
    column = node.range.start_point[1]
    errors = 0
    # Checking for syntax errors (already detected by parser / grammar).
    # These are represented in the syntax tree as special ERROR nodes.
    if node.type == "ERROR":
        _highlight_range(node, lines)
        print(f"Error: Syntax error at {filename}:{line}:{column}")
        errors += 1

    if node.type == "attribute_name":
        if _text(node) == "ifvarclass":
            _highlight_range(node, lines)
            print(
                f"Error: Use 'if' instead of 'ifvarclass' (deprecated) at {filename}:{line}:{column}"
            )
            errors += 1

    for node in node.children:
        errors += _walk(filename, lines, node)

    return errors


def lint_policy_file(filename):
    assert os.path.isfile(filename)
    assert filename.endswith(".cf")
    PY_LANGUAGE = Language(tscfengine.language())
    parser = Parser(PY_LANGUAGE)

    with open(filename, "rb") as f:
        original_data = f.read()
    tree = parser.parse(original_data)
    lines = original_data.decode().split("\n")

    root_node = tree.root_node
    assert root_node.type == "source_file"
    errors = 0
    if not root_node.children:
        print(f"Error: Empty policy file '{filename}'")
        errors += 1
    errors += _walk(filename, lines, root_node)
    if errors == 0:
        print(f"PASS: {filename}")
        return 0

    print(f"FAIL: {filename} ({errors} error{'s' if errors > 0 else ''})")
    return errors
