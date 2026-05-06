import os
import tempfile

from cfengine_cli.lint_csv import check_csv_file, check_csv_record_terminators


def _write_temp_csv(content: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "wb") as f:
        f.write(content)
    return path


VALID = [
    ("crlf_terminated", b"a,b,c\r\n1,2,3\r\n"),
    ("crlf_no_trailing_newline", b"a,b,c\r\n1,2,3"),
    ("single_record_no_newline", b"a,b,c"),
    ("row_of_empty_fields", b",,\r\n"),
    ("lf_inside_quoted_field", b'a,"line1\nline2",c\r\n'),
    ("cr_inside_quoted_field", b'a,"line1\rline2",c\r\n'),
    ("crlf_inside_quoted_field", b'a,"line1\r\nline2",c\r\n'),
    ("escaped_quote_inside_field", b'a,"he said ""hi""",c\r\n'),
]

INVALID = [
    ("empty_file", b""),
    ("only_one_empty_line", b"\r\n"),
    ("only_empty_lines", b"\r\n\r\n\r\n"),
    ("lf_only_line_endings", b"a,b,c\n1,2,3\n"),
    ("cr_only_line_endings", b"a,b,c\r1,2,3\r"),
    ("mixed_crlf_then_bare_lf", b"a,b,c\r\n1,2,3\nx,y,z\r\n"),
    ("bare_cr_mid_record", b"a,b\rc,d\r\n"),
    ("trailing_bare_cr", b"a,b,c\r"),
    ("trailing_bare_lf", b"a,b,c\n"),
]


def test_check_csv_file_accepts_valid():
    for name, content in VALID:
        path = _write_temp_csv(content)
        try:
            assert check_csv_file(path) is None, f"Expected valid: {name}"
        finally:
            os.unlink(path)


def test_check_csv_file_rejects_invalid():
    for name, content in INVALID:
        path = _write_temp_csv(content)
        try:
            assert check_csv_file(path) is not None, f"Expected invalid: {name}"
        finally:
            os.unlink(path)


def test_check_csv_record_terminators_accepts_crlf():
    assert check_csv_record_terminators("a,b\r\nc,d\r\n") is None


def test_check_csv_record_terminators_allows_newlines_inside_quotes():
    assert check_csv_record_terminators('"a\nb\rc\r\nd"\r\n') is None


def test_check_csv_record_terminators_rejects_bare_lf():
    assert check_csv_record_terminators("a,b\nc,d\n") == "bare LF outside quoted field"


def test_check_csv_record_terminators_rejects_bare_cr():
    assert check_csv_record_terminators("a,b\rc,d") == "bare CR outside quoted field"


def test_check_csv_record_terminators_rejects_trailing_bare_cr():
    assert check_csv_record_terminators("a,b\r") == "bare CR outside quoted field"
