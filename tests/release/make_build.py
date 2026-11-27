"""Generate a fake build-in-container output from a published release document.

Usage: make_build.py DOCUMENT DEB RPM OUTPUT_DIR

Every artifact becomes a file named as in its URL, in the directory the build
has it in. .deb and .rpm files are copies of DEB and RPM, small real packages,
so they can be signed. Other files are a few fake bytes.
"""

import hashlib
import json
import sys
from pathlib import Path


def _build_dir(artifact: dict[str, str]) -> str:
    """Return the build directory of an artifact."""
    title = artifact["Title"]
    if title in (
        "Source code tarball",
        "Masterfiles source tarball",
        "Masterfiles ready-to-install tarball",
    ):
        return "tarballs"
    if title == "Linux binary tarball (unsupported)":
        return "PACKAGES_x86_64_linux_redhat_7"
    if title == "Vagrant Environment":
        return "vagrant"
    return artifact["package"]


def _build_name(artifact: dict[str, str]) -> str:
    """Return the file name in the build."""
    name = artifact["URL"].rsplit("/", 1)[-1]
    if artifact["Title"] == "Source code tarball":
        # Published as cfengine-community-3.29.0.tar.gz, built as cfengine-3.29.0.tar.gz
        return name.replace("cfengine-community-", "cfengine-", 1)
    return name


def main(document: str, deb: str, rpm: str, output_dir: str) -> None:
    data = json.loads(Path(document).read_text())
    packages = {".deb": Path(deb).read_bytes(), ".rpm": Path(rpm).read_bytes()}
    output = Path(output_dir)
    for artifacts in data["artifacts"].values():
        for artifact in artifacts:
            name = _build_name(artifact)
            path = output / _build_dir(artifact) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            content = packages.get(path.suffix, f"fake {name}\n".encode())
            _ = path.write_bytes(content)

    for directory in output.iterdir():
        lines = [
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in sorted(directory.iterdir())
        ]
        _ = (directory / "sha256sums.txt").write_text("".join(lines))


if __name__ == "__main__":
    main(*sys.argv[1:])
