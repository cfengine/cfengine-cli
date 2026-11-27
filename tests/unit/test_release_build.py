import shutil
from pathlib import Path

import pytest

from cfengine_cli.release.build import read_build
from cfengine_cli.utils import UserError

HUB = "PACKAGES_HUB_x86_64_linux_debian_12"
AGENT = "PACKAGES_x86_64_linux_redhat_9"


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


@pytest.fixture
def build_dir(tmp_path: Path) -> Path:
    _touch(tmp_path / HUB / "cfengine-nova-hub_3.30.0-1_amd64.deb")
    _touch(tmp_path / HUB / "cfengine-nova-hub-3.30.0-1.x86_64.pkg.tar.gz")
    _touch(tmp_path / HUB / "sha256sums.txt")
    _touch(tmp_path / AGENT / "cfengine-nova-3.30.0-1.el9.x86_64.rpm")
    _touch(tmp_path / AGENT / "sha256sums.txt")
    _touch(tmp_path / "tarballs" / "cfengine-masterfiles-3.30.0.tar.gz")
    _touch(tmp_path / "tarballs" / "cfengine-3.30.0.tar.gz")
    _touch(tmp_path / "tarballs" / "sha256sums.txt")
    return tmp_path


def test_read_build(build_dir: Path) -> None:
    build = read_build(str(build_dir))
    assert {k: [p.name for p in v.packages] for k, v in build.labels.items()} == {
        HUB: [
            "cfengine-nova-hub-3.30.0-1.x86_64.pkg.tar.gz",
            "cfengine-nova-hub_3.30.0-1_amd64.deb",
        ],
        AGENT: ["cfengine-nova-3.30.0-1.el9.x86_64.rpm"],
    }
    assert build.labels[HUB].sha256sums == build_dir / HUB / "sha256sums.txt"

    assert [p.name for p in build.tarballs.packages] == [
        "cfengine-3.30.0.tar.gz",
        "cfengine-masterfiles-3.30.0.tar.gz",
    ]
    assert build.tarballs.sha256sums == build_dir / "tarballs" / "sha256sums.txt"
    assert build.vagrant is None


def test_read_build_with_vagrant(build_dir: Path) -> None:
    tarball = "CFEngine_Enterprise_vagrant_quickstart-3.30.0-1.tar.gz"
    _touch(build_dir / "vagrant" / tarball)
    _touch(build_dir / "vagrant" / "sha256sums.txt")
    build = read_build(str(build_dir))
    assert build.vagrant is not None
    assert [p.name for p in build.vagrant.packages] == [tarball]


def test_read_build_vagrant_without_sha256sums(build_dir: Path) -> None:
    _touch(
        build_dir / "vagrant" / "CFEngine_Enterprise_vagrant_quickstart-3.30.0-1.tar.gz"
    )
    with pytest.raises(UserError, match="No sha256sums.txt"):
        _ = read_build(str(build_dir))


def test_read_build_without_tarballs(build_dir: Path) -> None:
    shutil.rmtree(build_dir / "tarballs")
    with pytest.raises(UserError, match="No tarballs directory"):
        _ = read_build(str(build_dir))


def test_read_build_label_without_packages(build_dir: Path) -> None:
    _touch(build_dir / "PACKAGES_x86_64_linux_ubuntu_24" / "sha256sums.txt")
    with pytest.raises(UserError, match="No packages"):
        _ = read_build(str(build_dir))


def test_read_build_label_without_sha256sums(build_dir: Path) -> None:
    (build_dir / HUB / "sha256sums.txt").unlink()
    with pytest.raises(UserError, match="No sha256sums.txt"):
        _ = read_build(str(build_dir))


def test_read_build_unexpected_entry(build_dir: Path) -> None:
    _touch(build_dir / "stray.txt")
    with pytest.raises(UserError, match="Unexpected"):
        _ = read_build(str(build_dir))


def test_read_build_no_labels(tmp_path: Path) -> None:
    with pytest.raises(UserError, match="No PACKAGES_"):
        _ = read_build(str(tmp_path))
