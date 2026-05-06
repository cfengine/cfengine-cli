import os
import tempfile

from cfengine_cli.lint_yml import check_yml_file


def _write_temp_yml(content: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".yml")
    with os.fdopen(fd, "wb") as f:
        f.write(content)
    return path


VALID = [
    ("simple_mapping", b"key: value\n"),
    ("nested_mapping", b"top:\n  nested: value\n  list:\n    - 1\n    - 2\n"),
    ("flow_sequence", b"items: [1, 2, 3]\n"),
    ("flow_mapping", b"obj: {a: 1, b: 2}\n"),
    ("multi_document", b"---\na: 1\n---\nb: 2\n"),
    ("scalar_only", b"42\n"),
    ("string_only", b'"hello"\n'),
    ("list_only", b"- one\n- two\n"),
    ("multi_doc_first_null", b"---\n---\nname: cfengine\n"),
    ("only_null_document", b"---\n"),
    ("multiple_null_documents", b"---\n---\n---\n"),
]

INVALID = [
    ("empty_file", b""),
    ("only_whitespace", b"   \n\n"),
    ("unclosed_flow_sequence", b"items: [1, 2, 3\n"),
    ("unclosed_flow_mapping", b"obj: {a: 1, b: 2\n"),
    ("bad_indentation", b"top:\n nested: value\n  bad: value\n"),
    ("tab_indentation", b"top:\n\tnested: value\n"),
    ("duplicate_key_via_alias", b"a: &x 1\nb: *y\n"),
]


def test_check_yml_file_accepts_valid():
    for name, content in VALID:
        path = _write_temp_yml(content)
        try:
            assert check_yml_file(path) is None, f"Expected valid: {name}"
        finally:
            os.unlink(path)


def test_check_yml_file_rejects_invalid():
    for name, content in INVALID:
        path = _write_temp_yml(content)
        try:
            assert check_yml_file(path) is not None, f"Expected invalid: {name}"
        finally:
            os.unlink(path)
