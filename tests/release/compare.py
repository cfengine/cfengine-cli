"""Compare a release-data file with the published one.

Usage: compare.py EXPECTED ACTUAL VERSION

Ignores what a re-release with fake packages cannot reproduce: the SHA256 of
the artifacts, and the release date of VERSION in releases.json. Compares the
rest as formatted text, so the order of keys and lists counts too.
"""

import difflib
import json
import sys
from pathlib import Path
from typing import Any


def _normalized(path: str, version: str) -> list[str]:
    data: dict[str, Any] = json.loads(Path(path).read_text())
    for artifacts in data.get("artifacts", {}).values():
        for artifact in artifacts:
            del artifact["SHA256"]
    for release in data.get("releases", []):
        if release["version"] == version:
            del release["release_date"]
    return json.dumps(data, indent=4).splitlines(keepends=True)


def main(expected: str, actual: str, version: str) -> None:
    diff = list(
        difflib.unified_diff(
            _normalized(expected, version),
            _normalized(actual, version),
            expected,
            actual,
        )
    )
    if diff:
        sys.stdout.writelines(diff)
        sys.exit(f"{actual} differs from {expected}")


if __name__ == "__main__":
    main(*sys.argv[1:])
