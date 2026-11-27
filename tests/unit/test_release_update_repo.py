from pathlib import Path

import pytest

from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.update_repo import RepoFile, plan_repo, update_repos
from cfengine_cli.utils import UserError

BUILD = Path("/build")
RELEASE = Path("/output/release")
REPO = Path("/output/repo")


def _planned(label: str | None, name: str, debug: bool = False) -> PlannedFile:
    return PlannedFile(
        source=BUILD / str(label) / name,
        destination=None if debug else RELEASE / name,
        url="url",
        section="Section",
        title="Title",
        arch="x86_64",
        classexpr="any",
        package=label,
    )


def test_plan_repo() -> None:
    deb = "cfengine-community_3.30.0-1_amd64.deb"
    rpm = "cfengine-community-3.30.0-1.el9.aarch64.rpm"
    planned = [
        _planned("PACKAGES_x86_64_linux_debian_12", deb),
        _planned("PACKAGES_arm_64_linux_redhat_9", rpm),
        # Not in the repos
        _planned("PACKAGES_x86_64_linux_ubuntu_24", "cfengine-community_ubuntu.deb"),
        _planned(None, "cfengine-masterfiles-3.30.0.tar.gz"),
    ]
    # The signed copies in the release dir
    assert plan_repo(planned, "/output") == [
        RepoFile(RELEASE / deb, REPO / "apt/packages/pool/main/C" / deb),
        RepoFile(RELEASE / rpm, REPO / "yum/aarch64" / rpm),
    ]


def test_plan_repo_debug() -> None:
    planned = [_planned("PACKAGES_x86_64_linux_debian_12", "a.deb", debug=True)]
    assert plan_repo(planned, "/output") == []


def test_update_repos_missing_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    _ = (tmp_path / "a.deb").write_text("deb")
    files = [RepoFile(tmp_path / "a.deb", tmp_path / "repo" / "a.deb")]
    with pytest.raises(UserError, match="Repository tools not found"):
        update_repos(files, str(tmp_path), dry_run=True)


def test_update_repos_not_released(tmp_path: Path) -> None:
    rpm = RELEASE / "cfengine-community-3.30.0-1.el9.x86_64.rpm"
    files = [RepoFile(rpm, tmp_path / "repo" / rpm.name)]
    with pytest.raises(UserError, match="run cfengine dev release first"):
        update_repos(files, str(tmp_path), dry_run=True)
