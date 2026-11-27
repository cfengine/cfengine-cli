from pathlib import Path

import pytest

from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.copy_files import copy_files
from cfengine_cli.utils import UserError


def _planned(source: Path, destination: Path | None) -> PlannedFile:
    return PlannedFile(
        source=source,
        destination=destination,
        url="url",
        section="Section",
        title="Title",
        arch="x86_64",
        classexpr="any",
        package=None,
    )


def _built(tmp_path: Path, name: str) -> Path:
    source = tmp_path / "build" / name
    source.parent.mkdir(exist_ok=True)
    _ = source.write_text("built")
    return source


@pytest.fixture
def tarball(tmp_path: Path) -> Path:
    """Copied, but not signed."""
    return _built(tmp_path, "cfengine-masterfiles-3.30.0-1.pkg.tar.gz")


@pytest.fixture
def rpm(tmp_path: Path) -> Path:
    """Signed when copied, so these tests never copy it."""
    return _built(tmp_path, "cfengine-nova-3.30.0-1.el9.x86_64.rpm")


def test_copy_files(tmp_path: Path, tarball: Path) -> None:
    destination = tmp_path / "release" / tarball.name
    copy_files([_planned(tarball, destination)], str(tmp_path), dry_run=False)
    assert destination.read_text() == "built"
    # No temporary dir left
    assert list(tmp_path.glob(".tmp-*")) == []


def test_copy_files_skips_existing(
    tmp_path: Path, tarball: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "release" / tarball.name
    destination.parent.mkdir()
    _ = destination.write_text("published")
    copy_files([_planned(tarball, destination)], str(tmp_path), dry_run=False)
    assert destination.read_text() == "published"
    assert f"Warning: Skipped existing '{destination}'" in capsys.readouterr().out


def test_copy_files_skips_debug(
    tmp_path: Path, rpm: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copy_files([_planned(rpm, None)], str(tmp_path), dry_run=False)
    assert capsys.readouterr().out == ""


def test_copy_files_dry_run(
    tmp_path: Path, tarball: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "release" / tarball.name
    copy_files([_planned(tarball, destination)], str(tmp_path), dry_run=True)
    assert not destination.parent.exists()
    assert capsys.readouterr().out == (
        f"Would have copied '{tarball}' to '{destination}'\n"
    )


def test_copy_files_missing_signing_tools(
    tmp_path: Path, rpm: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    destination = tmp_path / "release" / rpm.name
    with pytest.raises(UserError, match="Signing tools not found"):
        copy_files([_planned(rpm, destination)], str(tmp_path), dry_run=True)
