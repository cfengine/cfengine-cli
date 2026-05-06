"""CSV file validation per RFC 4180.

The grammar in RFC 4180 mandates CRLF between records. Bare \\r or \\n
outside of quoted fields is not valid. Inside quoted fields, \\r and \\n
are allowed as field content.
"""

import csv


def check_csv_record_terminators(raw: str) -> str | None:
    """Check that all record terminators in a CSV string are CRLF.

    Returns None if all record terminators are CRLF, otherwise a short
    description of the problem.
    """
    in_quotes = False
    _prev = None
    prev = None
    for current in raw:
        prev = _prev
        _prev = current
        if current == '"':
            in_quotes = not in_quotes
            continue
        if in_quotes:
            continue
        if current == "\n" and prev != "\r":
            return "bare LF outside quoted field"
        if prev == "\r" and current != "\n":
            return "bare CR outside quoted field"
    if _prev == "\r" and not in_quotes:
        return "bare CR outside quoted field"
    return None


def check_csv_file(filename: str) -> str | None:
    """Check a CSV file: parses, has at least one non-empty record, and uses
    CRLF record terminators.

    Returns None if valid, otherwise a short description of the problem.
    """
    try:
        with open(filename, newline="") as f:
            raw = f.read()
        with open(filename, newline="") as f:
            rows = list(csv.reader(f, strict=True))
    except (OSError, csv.Error) as e:
        return str(e)
    if not any(rows):
        return "no records"
    return check_csv_record_terminators(raw)
