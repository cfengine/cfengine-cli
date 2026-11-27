import datetime
import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from cfengine_cli.release.metadata import ReleasesData, VersionDocument
from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.release_data import build_artifacts, write_release_data
from cfengine_cli.utils import UserError

TODAY = datetime.date(2027, 6, 1)


def _setup(tmp_path: Path) -> tuple[list[PlannedFile], Path]:
    source = tmp_path / "cfengine-masterfiles-3.30.0-1.pkg.tar.gz"
    _ = source.write_bytes(b"tarball")
    planned = [
        PlannedFile(
            source=source,
            destination=source,
            url="url",
            section="Additional Assets",
            title="Masterfiles ready-to-install tarball",
            arch="no arch",
            classexpr="!any",
            package=None,
        )
    ]
    directory = tmp_path / "out" / "release-data" / "community"
    directory.mkdir(parents=True)
    _ = (directory / "releases.json").write_text('{"lts_branches": [], "releases": []}')
    return planned, directory


def test_write_release_data(tmp_path: Path) -> None:
    planned, directory = _setup(tmp_path)
    write_release_data(
        "community",
        "3.30.0",
        "3.30.x",
        False,
        planned,
        str(tmp_path / "out"),
        dry_run=False,
        today=TODAY,
    )
    text = (directory / "3.30.0.json").read_text()
    document = cast(VersionDocument, json.loads(text))
    assert document["version"] == "3.30.0 LTS"
    assert list(document.get("artifacts", {})) == ["Additional Assets"]
    text = (directory / "releases.json").read_text()
    releases = cast(ReleasesData, json.loads(text))
    assert [r["version"] for r in releases["releases"]] == ["3.30.0"]


def test_write_release_data_dry_run(tmp_path: Path) -> None:
    planned, directory = _setup(tmp_path)
    write_release_data(
        "community",
        "3.30.0",
        "3.30.x",
        False,
        planned,
        str(tmp_path / "out"),
        dry_run=True,
        today=TODAY,
    )
    assert not (directory / "3.30.0.json").exists()
    assert (directory / "releases.json").read_text() == (
        '{"lts_branches": [], "releases": []}'
    )


def test_write_release_data_invalid_releases(tmp_path: Path) -> None:
    planned, directory = _setup(tmp_path)
    _ = (directory / "releases.json").write_text('{"releases": [')
    with pytest.raises(UserError, match="Invalid JSON in"):
        write_release_data(
            "community",
            "3.30.0",
            "3.30.x",
            False,
            planned,
            str(tmp_path / "out"),
            dry_run=True,
            today=TODAY,
        )


def _write(path: Path, content: bytes) -> Path:
    _ = path.write_bytes(content)
    return path


def test_build_artifacts(tmp_path: Path) -> None:
    deb = PlannedFile(
        source=_write(tmp_path / "unsigned.deb", b"unsigned"),
        destination=_write(tmp_path / "signed.deb", b"signed"),
        url="https://example.com/signed.deb",
        section="Binary packages",
        title="Debian 12",
        arch="x86_64",
        classexpr="debian_12.x86_64",
        package="PACKAGES_x86_64_linux_debian_12",
    )
    tarball = PlannedFile(
        source=_write(tmp_path / "source.tar.gz", b"tarball"),
        destination=_write(tmp_path / "copy.tar.gz", b"tarball"),
        url="https://example.com/copy.tar.gz",
        section="Additional Assets",
        title="Linux binary tarball (unsupported)",
        arch="x86_64",
        classexpr="!any",
        package=None,
        instructions="https://docs.example.com",
        footnote="Not supported",
    )
    artifacts, footnotes = build_artifacts([deb, tarball], dry_run=False)
    assert artifacts == {
        "Binary packages": [
            {
                "Title": "Debian 12",
                "Arch": "x86_64",
                "classexpr": "debian_12.x86_64",
                "Published": True,
                "URL": "https://example.com/signed.deb",
                # Of the signed copy
                "SHA256": hashlib.sha256(b"signed").hexdigest(),
                "package": "PACKAGES_x86_64_linux_debian_12",
            }
        ],
        "Additional Assets": [
            {
                "Title": "Linux binary tarball (unsupported)",
                "Arch": "x86_64",
                "classexpr": "!any",
                "Published": True,
                "URL": "https://example.com/copy.tar.gz",
                "SHA256": hashlib.sha256(b"tarball").hexdigest(),
                "Footnote": 1,
                "Instructions": "https://docs.example.com",
            }
        ],
    }
    assert footnotes == ["Not supported"]
    # Key order as in the legacy release.py
    assert list(artifacts["Additional Assets"][0]) == [
        "Title",
        "Arch",
        "classexpr",
        "Published",
        "URL",
        "SHA256",
        "Footnote",
        "Instructions",
    ]


def test_build_artifacts_dry_run(tmp_path: Path) -> None:
    # Nothing is copied in a dry run, so the source is checksummed
    deb = PlannedFile(
        source=_write(tmp_path / "unsigned.deb", b"unsigned"),
        destination=tmp_path / "not-copied.deb",
        url="url",
        section="Binary packages",
        title="Debian 12",
        arch="x86_64",
        classexpr="debian_12.x86_64",
        package="PACKAGES_x86_64_linux_debian_12",
    )
    artifacts, _ = build_artifacts([deb], dry_run=True)
    sha256 = artifacts["Binary packages"][0]["SHA256"]
    assert sha256 == hashlib.sha256(b"unsigned").hexdigest()
