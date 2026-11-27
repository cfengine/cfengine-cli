import fcntl
from pathlib import Path

import pytest

from cfengine_cli.release.utils import atomic_write, output_lock


def test_atomic_write_error(tmp_path: Path) -> None:
    destination = tmp_path / "release" / "cfengine-nova_3.30.0-1_amd64.deb"
    with pytest.raises(RuntimeError):
        with atomic_write(destination, str(tmp_path)) as temporary:
            _ = temporary.write_text("half written")
            raise RuntimeError
    assert not destination.exists()
    assert list(tmp_path.glob(".tmp-*")) == []


def _try_lock(path: Path) -> bool:
    """Return True if the lock is free, as another release would see it."""
    with open(path, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False


def test_output_lock(tmp_path: Path) -> None:
    with output_lock(str(tmp_path), dry_run=False):
        assert not _try_lock(tmp_path / ".lock")
    assert _try_lock(tmp_path / ".lock")


def test_output_lock_dry_run(tmp_path: Path) -> None:
    output = tmp_path / "output"
    with output_lock(str(output), dry_run=True):
        pass
    assert not output.exists()
