import fcntl
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType
from typing import NoReturn

from cfengine_cli.utils import UserError

SIGNED_SUFFIXES = (".rpm", ".deb")
# Signs the packages and the repo metadata. Always named, as gpg silently
# falls back to the default key for --default-key or no key.
SIGNING_KEY = "contact@northern.tech"
# In the output dir. Also taken by the legacy release.py in infra.
LOCK_FILE = ".lock"
# Free space to keep on top of the files to copy, as in the legacy release.py.
# Also covers the repo metadata that update-repo regenerates.
DISK_SPACE_MARGIN = 1024**3
AR_MAGIC = b"!<arch>\n"


def exit_on_sigterm() -> None:
    """Exit cleanly on SIGTERM, e.g. from an aborted Jenkins job.

    Python's default is to die at once, which leaves temporary files behind.
    sys.exit() raises SystemExit, so they are removed on the way out.
    """

    def handler(_signum: int, _frame: FrameType | None) -> NoReturn:
        sys.exit(1)

    _ = signal.signal(signal.SIGTERM, handler)


def run(command: list[str]) -> str:
    """Run a command and return its stdout. stderr goes to the terminal."""
    try:
        return subprocess.run(
            command, check=True, stdout=subprocess.PIPE, text=True
        ).stdout
    except subprocess.CalledProcessError as e:
        # A UserError, as a failed command is not a bug in cfengine-cli
        raise UserError(f"Command failed: {' '.join(command)}") from e


def _deb_build_time(path: Path) -> int:
    """Return the mtime of the first ar member, set from SOURCE_DATE_EPOCH."""
    with open(path, "rb") as f:
        header = f.read(len(AR_MAGIC) + 60)
    if not header.startswith(AR_MAGIC) or len(header) < len(AR_MAGIC) + 60:
        raise UserError(f"Not a .deb: '{path}'")
    # An ar member header starts with a 16 byte name, then a 12 byte mtime
    mtime = header[len(AR_MAGIC) + 16 : len(AR_MAGIC) + 28]
    return int(mtime.decode("ascii"))


def _rpm_build_time(path: Path) -> int:
    """Return BUILDTIME, set from SOURCE_DATE_EPOCH by build-in-container."""
    # Skip signature checking. The package is not signed yet, and checking
    # needs the rpm database, which Debian hosts lack.
    return int(run(["rpm", "-qp", "--nosignature", "--qf", "%{BUILDTIME}", str(path)]))


def is_signed_deb(path: Path) -> bool:
    """Return True if the deb has an origin signature, as debsigs adds."""
    with open(path, "rb") as f:
        if f.read(len(AR_MAGIC)) != AR_MAGIC:
            raise UserError(f"Not a .deb: '{path}'")
        # Each ar member has a 60 byte header: a 16 byte name, and the size
        # at bytes 48 to 58. Members start at even offsets.
        while len(header := f.read(60)) == 60:
            name = header[:16].rstrip(b" ").rstrip(b"/")
            if name == b"_gpgorigin":
                return True
            size = int(header[48:58].decode("ascii"))
            _ = f.seek(size + size % 2, os.SEEK_CUR)
    return False


def is_signed(path: Path) -> bool:
    """Return True if the .rpm or .deb has a signature."""
    if path.name.endswith(".rpm"):
        return is_signed_rpm(path)
    return is_signed_deb(path)


def is_signed_rpm(path: Path) -> bool:
    """Return True if the rpm has a signature, as rpmsign adds."""
    # rpmsign of rpm 4 signs into RSAHEADER, of rpm 6 into OPENPGP. rpm 4 does
    # not know OPENPGP, and prints nothing for it. --nosignature as in
    # _rpm_build_time(). Only checks that a signature is there, verifying it
    # would need the key in an rpm database.
    for tag in ("RSAHEADER", "OPENPGP"):
        query = ["rpm", "-qp", "--nosignature", "--qf", f"%{{{tag}:pgpsig}}"]
        if run([*query, str(path)]).strip() not in ("", "(none)"):
            return True
    return False


def build_time(path: Path) -> int:
    """Return the package's SOURCE_DATE_EPOCH."""
    if path.name.endswith(".rpm"):
        return _rpm_build_time(path)
    return _deb_build_time(path)


def sign(path: Path, time: int) -> None:
    """Sign a .rpm or .deb with the given signature creation time.

    A fixed time makes the signed package reproducible with the same key.
    """
    # The "!" stops the faked clock, so the time does not tick during signing
    faked_time = f"--faked-system-time {time}!"
    if path.name.endswith(".rpm"):
        _ = run(
            [
                "rpmsign",
                "--resign",
                "--digest-algo=sha256",
                "--define",
                f"_gpg_name {SIGNING_KEY}",
                "--define",
                f"_gpg_sign_cmd_extra_args {faked_time}",
                str(path),
            ]
        )
    else:
        # debsigs has no strict key option, its -k is --default-key
        gpgopts = f"{faked_time} --local-user {SIGNING_KEY}"
        _ = run(["debsigs", "--sign=origin", f"--gpgopts={gpgopts}", str(path)])
        # debsigs can print an error, yet exit 0 with an unsigned package.
        # So check that the signature is there and good.
        _ = run(["debsigs", "--verify", str(path)])


def check_tools(kind: str, tools: tuple[str, ...]) -> None:
    """Fail before any work if a tool is missing, e.g. kind "Signing"."""
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        raise UserError(f"{kind} tools not found: {', '.join(missing)}")


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
        # The destination name, as sign() needs the .rpm or .deb suffix
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
    source: Path, destination: Path, output_dir: str, *, signed: bool, dry_run: bool
) -> None:
    """Copy source to destination unless it exists, and print what is done."""
    if destination.exists():
        # Already there, e.g. from an earlier run that failed later on
        print(f"Warning: Skipped existing '{destination}'")
        return
    if dry_run:
        print(f"Would have copied '{source}' to '{destination}'")
        if signed:
            print(f"Would have signed '{destination}'")
        return
    copy_file(source, destination, output_dir, signed=signed)
    print(f"Copied '{source}' to '{destination}'{' and signed' if signed else ''}")


def copy_file(
    source: Path, destination: Path, output_dir: str, *, signed: bool
) -> None:
    """Copy source to destination, and sign the copy if signed.

    The copy is written in a temporary directory in output_dir, see
    atomic_write().
    """
    with atomic_write(destination, output_dir) as temporary:
        _ = shutil.copyfile(source, temporary)
        if signed:
            sign(temporary, build_time(source))
