import fcntl
import shutil
import signal
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType
from typing import NoReturn

from cfengine_cli.utils import UserError

# In the output dir. Also taken by the legacy release.py in infra.
LOCK_FILE = ".lock"
# Free space to keep on top of the files to copy, as in the legacy release.py.
DISK_SPACE_MARGIN = 1024**3


def exit_on_sigterm() -> None:
    """Exit cleanly on SIGTERM, e.g. from an aborted Jenkins job.

    Python's default is to die at once, which leaves temporary files behind.
    sys.exit() raises SystemExit, so they are removed on the way out.
    """

    def handler(_signum: int, _frame: FrameType | None) -> NoReturn:
        sys.exit(1)

    _ = signal.signal(signal.SIGTERM, handler)


@contextmanager
def atomic_write(destination: Path, output_dir: str) -> Generator[Path, None, None]:
    """Yield a temporary file to write, then rename it to destination.

    So a file at the destination is always complete. The temporary file is in
    a unique directory in the output dir, outside release/, repo/ and
    release-data/. So no repo tool or upload picks it up, also not those of
    the legacy release.py, and parallel runs never write the same file. It is
    on the same filesystem, so the rename is atomic.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Removed with its contents on errors, also on Ctrl-C. Only SIGKILL or a
    # crash leaves it behind.
    with tempfile.TemporaryDirectory(dir=output_dir, prefix=".tmp-") as directory:
        temporary = Path(directory) / destination.name
        yield temporary
        _ = temporary.rename(destination)


@contextmanager
def output_lock(output_dir: str, *, dry_run: bool) -> Generator[None, None, None]:
    """Hold an exclusive lock on the output dir while writing to it.

    Runs write the same releases.json and repos, so they must not overlap.
    The legacy release.py takes the same lock. The kernel releases it when
    the process ends, also on SIGKILL. A dry run only reads, so takes none.
    """
    if dry_run:
        yield
        return
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(Path(output_dir) / LOCK_FILE, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Waiting for another release to finish ...", flush=True)
            fcntl.flock(f, fcntl.LOCK_EX)
        yield


def _existing_parent(path: Path) -> Path:
    while not path.exists():
        path = path.parent
    return path


def check_disk_space(copies: list[tuple[Path, Path | None]], output_dir: str) -> None:
    """Fail unless output_dir fits the copies, plus a margin.

    copies are (source, destination) pairs. Destinations that are None or
    exist already are not copied, so they are not counted.
    """
    sizes = [
        source.stat().st_size
        for source, destination in copies
        if destination is not None and not destination.exists()
    ]
    if not sizes:
        return
    needed = sum(sizes) + DISK_SPACE_MARGIN
    # The output dir may not exist yet, e.g. locally
    free = shutil.disk_usage(_existing_parent(Path(output_dir))).free
    if free < needed:
        raise UserError(
            f"Not enough disk space in '{output_dir}': "
            + f"need ~{needed // 1024**2} MiB, only {free // 1024**2} MiB free"
        )


def copy_or_skip(
    source: Path, destination: Path, output_dir: str, *, dry_run: bool
) -> None:
    """Copy source to destination unless it exists, and print what is done."""
    if destination.exists():
        # Already there, e.g. from an earlier run that failed later on
        print(f"Warning: Skipped existing '{destination}'")
        return
    if dry_run:
        print(f"Would have copied '{source}' to '{destination}'")
        return
    copy_file(source, destination, output_dir)
    print(f"Copied '{source}' to '{destination}'")


def copy_file(source: Path, destination: Path, output_dir: str) -> None:
    """Copy source to destination.

    The copy is written in a temporary directory in output_dir, see
    atomic_write().
    """
    with atomic_write(destination, output_dir) as temporary:
        _ = shutil.copyfile(source, temporary)
