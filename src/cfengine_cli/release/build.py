from dataclasses import dataclass
from pathlib import Path

from cfengine_cli.utils import UserError

LABEL_PREFIX = "PACKAGES_"
TARBALLS_DIR = "tarballs"
VAGRANT_DIR = "vagrant"
SHA256SUMS = "sha256sums.txt"
# .tar.gz also covers .pkg.tar.gz
PACKAGE_SUFFIXES = (".deb", ".rpm", ".msi", ".tar.gz")


@dataclass
class PackageDir:
    packages: list[Path]
    sha256sums: Path


@dataclass
class Build:
    labels: dict[str, PackageDir]
    tarballs: PackageDir
    # The Vagrant quickstart. Only enterprise builds have it.
    vagrant: PackageDir | None
    # Name of the build dir, e.g. jenkins-master-nightly-pipeline-123.
    # Nightlies link to the packages under it on buildcache.
    name: str


def _read_package_dir(directory: Path) -> PackageDir:
    packages = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.name.endswith(PACKAGE_SUFFIXES)
    )
    if not packages:
        raise UserError(f"No packages in '{directory}'")

    sha256sums = directory / SHA256SUMS
    if not sha256sums.is_file():
        raise UserError(f"No {SHA256SUMS} in '{directory}'")

    return PackageDir(packages, sha256sums)


def read_build(build_dir: str) -> Build:
    """Read a build-in-container output directory.

    It has one subdirectory per label, e.g. PACKAGES_x86_64_linux_debian_12,
    a tarballs subdirectory, and optionally a vagrant subdirectory.
    """
    labels: dict[str, PackageDir] = {}
    tarballs: PackageDir | None = None
    vagrant: PackageDir | None = None

    for entry in sorted(Path(build_dir).iterdir()):
        if entry.is_dir() and entry.name.startswith(LABEL_PREFIX):
            labels[entry.name] = _read_package_dir(entry)
        elif entry.is_dir() and entry.name == TARBALLS_DIR:
            tarballs = _read_package_dir(entry)
        elif entry.is_dir() and entry.name == VAGRANT_DIR:
            vagrant = _read_package_dir(entry)
        else:
            raise UserError(f"Unexpected '{entry}' in build")

    if not labels:
        raise UserError(f"No {LABEL_PREFIX}* directories in '{build_dir}'")
    if tarballs is None:
        raise UserError(f"No {TARBALLS_DIR} directory in '{build_dir}'")
    return Build(labels, tarballs, vagrant, Path(build_dir).resolve().name)
