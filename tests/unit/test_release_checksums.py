import hashlib
from pathlib import Path

import pytest

from cfengine_cli.release.checksums import parse_checksums, verify_checksums
from cfengine_cli.utils import UserError

FILES = {
    "cfengine-nova-3.30.0-1.el9.x86_64.rpm": b"rpm",
    "cfengine-nova_3.30.0-1_amd64.deb": b"deb",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def manifest(tmp_path: Path) -> Path:
    """A directory with FILES and a manifest listing them, as sha256sum writes it."""
    lines: list[str] = []
    for name, data in sorted(FILES.items()):
        _ = (tmp_path / name).write_bytes(data)
        lines.append(f"{_sha256(data)}  {name}\n")
    path = tmp_path / "sha256sums.txt"
    _ = path.write_text("".join(lines))
    return path


def test_parse_checksums(manifest: Path) -> None:
    assert parse_checksums(manifest) == {
        name: _sha256(data) for name, data in FILES.items()
    }


def test_verify_checksums(manifest: Path) -> None:
    verify_checksums(manifest)


def test_verify_checksums_mismatch(manifest: Path) -> None:
    _ = (manifest.parent / "cfengine-nova_3.30.0-1_amd64.deb").write_bytes(b"x")
    with pytest.raises(UserError, match="Checksum mismatch"):
        verify_checksums(manifest)


def test_verify_checksums_missing_file(manifest: Path) -> None:
    (manifest.parent / "cfengine-nova_3.30.0-1_amd64.deb").unlink()
    with pytest.raises(UserError, match="Missing"):
        verify_checksums(manifest)


def test_verify_checksums_unlisted_file(manifest: Path) -> None:
    _ = (manifest.parent / "stray.txt").write_bytes(b"stray")
    with pytest.raises(UserError, match="Not listed"):
        verify_checksums(manifest)


def test_parse_checksums_invalid_line(manifest: Path) -> None:
    with manifest.open("a") as f:
        _ = f.write("not a checksum line\n")
    with pytest.raises(UserError, match="Invalid line 3"):
        _ = parse_checksums(manifest)


def test_parse_checksums_listed_twice(manifest: Path) -> None:
    first_line = manifest.read_text().splitlines(keepends=True)[0]
    with manifest.open("a") as f:
        _ = f.write(first_line)
    with pytest.raises(UserError, match="listed twice"):
        _ = parse_checksums(manifest)
