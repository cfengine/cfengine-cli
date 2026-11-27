import hashlib
import re
from pathlib import Path

from cfengine_cli.release.build import Build
from cfengine_cli.utils import UserError

# sha256sum output: hash, two spaces, file name
_LINE_RE = re.compile(r"([0-9a-f]{64})  (.+)")


def parse_checksums(manifest: Path) -> dict[str, str]:
    """Return a dict mapping each file name to its expected hash."""
    expected: dict[str, str] = {}
    # Count from 1, so error messages match the line numbers in an editor
    for number, line in enumerate(manifest.read_text().splitlines(), start=1):
        match = _LINE_RE.fullmatch(line)
        if not match:
            raise UserError(f"Invalid line {number} in '{manifest}'")
        digest, name = match.groups()
        if name in expected:
            raise UserError(f"'{name}' is listed twice in '{manifest}'")
        expected[name] = digest
    return expected


def verify_checksums(manifest: Path) -> None:
    """Check that the files next to sha256sums.txt are exactly the ones it lists.

    Fails if a listed file is missing, a file is not listed, or a hash differs.
    """
    directory = manifest.parent
    expected = parse_checksums(manifest)

    # Every file in the directory, except the checksum file itself
    actual: set[str] = set()
    for path in directory.iterdir():
        if path.is_file() and path != manifest:
            actual.add(path.name)

    missing = sorted(expected.keys() - actual)
    if missing:
        raise UserError(f"Missing in '{directory}': {', '.join(missing)}")
    unlisted = sorted(actual - expected.keys())
    if unlisted:
        raise UserError(f"Not listed in '{manifest}': {', '.join(unlisted)}")

    for name in sorted(expected):
        if file_sha256(directory / name) != expected[name]:
            raise UserError(f"Checksum mismatch for '{directory / name}'")


def verify_build(build: Build) -> None:
    """Verify the checksums of every directory in the build."""
    package_dirs = [*build.labels.values(), build.tarballs]
    if build.vagrant is not None:
        package_dirs.append(build.vagrant)
    for package_dir in package_dirs:
        verify_checksums(package_dir.sha256sums)
    print("Checksums OK")


def file_sha256(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()
