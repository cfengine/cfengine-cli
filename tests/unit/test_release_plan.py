from pathlib import Path

import pytest

from cfengine_cli.release.build import Build, PackageDir
from cfengine_cli.release.plan import (
    BINARY_TARBALL_FOOTNOTE,
    PlannedFile,
    plan_assets,
    plan_packages,
)
from cfengine_cli.utils import UserError

BUILD = Path("/builds/jenkins-master-nightly-pipeline-123")
OUTPUT = "/var/www/buildcache"
HUB = "PACKAGES_HUB_x86_64_linux_debian_12"
AGENT = "PACKAGES_x86_64_linux_redhat_9"
RHEL7 = "PACKAGES_x86_64_linux_redhat_7"
WINDOWS = "PACKAGES_x86_64_mingw"
S3 = "https://cfengine-package-repos.s3.amazonaws.com"
DOCS = "https://docs.cfengine.com/docs"

# Files in each label dir. Only .deb, .rpm and .msi are platform packages.
FILES = {
    HUB: [
        "cfengine-nova-hub-3.30.0-1.x86_64.pkg.tar.gz",
        "cfengine-nova-hub_3.30.0-1_amd64.deb",
    ],
    AGENT: ["cfengine-nova-3.30.0-1.el9.x86_64.rpm"],
    # The binary tarball is only published from this label
    RHEL7: [
        "cfengine-nova-3.30.0-1.el7.x86_64.rpm",
        "cfengine-nova-3.30.0-1.x86_64.pkg.tar.gz",
    ],
    WINDOWS: ["cfengine-nova-3.30.0-1-x86_64.msi"],
}
TARBALLS = [
    "cfengine-3.30.0.tar.gz",
    "cfengine-masterfiles-3.30.0-1.pkg.tar.gz",
    "cfengine-masterfiles-3.30.0.tar.gz",
]
VAGRANT = "CFEngine_Enterprise_vagrant_quickstart-3.30.0-1.tar.gz"


def _package_dir(label: str, names: list[str]) -> PackageDir:
    return PackageDir(
        [BUILD / label / name for name in names], BUILD / label / "sha256sums.txt"
    )


def _build(
    *labels: str, tarballs: list[str] = TARBALLS, vagrant: bool = False
) -> Build:
    """A build with the given labels. No files need to exist."""
    return Build(
        {label: _package_dir(label, FILES[label]) for label in labels},
        _package_dir("tarballs", tarballs),
        _package_dir("vagrant", [VAGRANT]) if vagrant else None,
        BUILD.name,
    )


def test_plan_packages_enterprise() -> None:
    planned = plan_packages("enterprise", "3.30.0", _build(HUB, AGENT), OUTPUT, False)
    hub_deb = "cfengine-nova-hub_3.30.0-1_amd64.deb"
    hub_path = "enterprise/Enterprise-3.30.0/hub/debian_12_x86_64"
    agent_rpm = "cfengine-nova-3.30.0-1.el9.x86_64.rpm"
    agent_path = "enterprise/Enterprise-3.30.0/agent/agent_rhel9_x86_64"
    # The hub's .pkg.tar.gz is not a platform package, so it is skipped
    assert planned == [
        PlannedFile(
            source=BUILD / HUB / hub_deb,
            destination=Path(OUTPUT) / "release" / hub_path / hub_deb,
            url=f"{S3}/{hub_path}/{hub_deb}",
            section="Policy Server",
            title="Debian 12",
            arch="x86_64",
            classexpr="am_policy_hub.debian_12.x86_64",
            package=HUB,
        ),
        PlannedFile(
            source=BUILD / AGENT / agent_rpm,
            destination=Path(OUTPUT) / "release" / agent_path / agent_rpm,
            url=f"{S3}/{agent_path}/{agent_rpm}",
            section="Hosts (Clients)",
            title="Red Hat / CentOS 9",
            arch="x86_64",
            classexpr="!am_policy_hub.(redhat_9|centos_9).x86_64",
            package=AGENT,
        ),
    ]


def test_plan_packages_community() -> None:
    [planned] = plan_packages("community", "3.30.0", _build(AGENT), OUTPUT, False)
    rpm = "cfengine-nova-3.30.0-1.el9.x86_64.rpm"
    path = "community_binaries/Community-3.30.0/agent_rhel9_x86_64"
    assert planned.destination == Path(OUTPUT) / "release" / path / rpm
    assert planned.url == f"{S3}/{path}/{rpm}"
    assert planned.section == "Binary packages"
    assert planned.classexpr == "(redhat_9|centos_9).x86_64"


def test_plan_packages_debug() -> None:
    [planned] = plan_packages("enterprise", "master", _build(AGENT), OUTPUT, True)
    assert planned.destination is None
    assert planned.url == (
        "http://buildcache.cfengine.com/packages/build-in-container/"
        f"jenkins-master-nightly-pipeline-123/{AGENT}/"
        "cfengine-nova-3.30.0-1.el9.x86_64.rpm"
    )


def test_plan_packages_windows() -> None:
    [planned] = plan_packages("enterprise", "3.30.0", _build(WINDOWS), OUTPUT, False)
    assert planned.source.name == "cfengine-nova-3.30.0-1-x86_64.msi"
    assert planned.url == (
        f"{S3}/enterprise/Enterprise-3.30.0/agent/windows_x86_64/"
        "cfengine-nova-3.30.0-1-x86_64.msi"
    )


def test_plan_assets_enterprise() -> None:
    planned = plan_assets(
        "enterprise",
        "3.30.0",
        _build(RHEL7, vagrant=True),
        OUTPUT,
        False,
    )
    # Checks which assets are planned, and that they are in the same order as
    # the legacy release.py lists them. No source tarballs, they are only
    # published with community releases.
    assert [p.title for p in planned] == [
        "Masterfiles ready-to-install tarball",
        "Linux binary tarball (unsupported)",
        "Vagrant Environment",
    ]
    assert all(p.section == "Additional Assets" for p in planned)
    assert all(p.classexpr == "!any" for p in planned)
    assert planned[0].package == "PACKAGES_VIRTUAL_PACKAGES_masterfiles"

    misc = "enterprise/Enterprise-3.30.0/misc"
    tarball = "cfengine-nova-3.30.0-1.x86_64.pkg.tar.gz"
    assert planned[1] == PlannedFile(
        source=BUILD / RHEL7 / tarball,
        destination=Path(OUTPUT) / "release" / misc / tarball,
        url=f"{S3}/{misc}/{tarball}",
        section="Additional Assets",
        title="Linux binary tarball (unsupported)",
        arch="x86_64",
        classexpr="!any",
        package=None,
        instructions=(
            f"{DOCS}/3.30/getting-started-installation-general-installation-"
            "installation-enterprise-generic-tarball.html"
        ),
        footnote=BINARY_TARBALL_FOOTNOTE,
    )
    assert planned[2].url == f"{S3}/{misc}/{VAGRANT}"


def test_plan_assets_community() -> None:
    planned = plan_assets("community", "3.30.0", _build(RHEL7), OUTPUT, False)
    # Checks which assets are planned, and that they are in the same order as
    # the legacy release.py lists them
    assert [p.title for p in planned] == [
        "Masterfiles ready-to-install tarball",
        "Linux binary tarball (unsupported)",
        "Source code tarball",
        "Masterfiles source tarball",
    ]
    assert planned[0].destination == (
        Path(OUTPUT)
        / "release/community_binaries/Community-3.30.0/misc"
        / "cfengine-masterfiles-3.30.0-1.pkg.tar.gz"
    )
    # The source tarball is published under a community name
    source = planned[2]
    assert source.source == BUILD / "tarballs" / "cfengine-3.30.0.tar.gz"
    assert source.destination == (
        Path(OUTPUT) / "release/tarballs/cfengine-community-3.30.0.tar.gz"
    )
    assert source.url == f"{S3}/tarballs/cfengine-community-3.30.0.tar.gz"
    assert planned[3].url == f"{S3}/tarballs/cfengine-masterfiles-3.30.0.tar.gz"


def test_plan_assets_debug() -> None:
    planned = plan_assets("community", "master", _build(RHEL7), OUTPUT, True)
    assert all(p.destination is None for p in planned)
    buildcache = (
        "http://buildcache.cfengine.com/packages/build-in-container/"
        "jenkins-master-nightly-pipeline-123"
    )
    assert planned[1].url == (
        f"{buildcache}/{RHEL7}/cfengine-nova-3.30.0-1.x86_64.pkg.tar.gz"
    )
    # Debug releases link to the source, so the source tarball keeps its name
    assert planned[2].url == f"{buildcache}/tarballs/cfengine-3.30.0.tar.gz"


def test_plan_assets_master_docs() -> None:
    planned = plan_assets("enterprise", "master", _build(RHEL7), OUTPUT, True)
    assert planned[1].instructions is not None
    assert planned[1].instructions.startswith(f"{DOCS}/master/")


def test_plan_assets_without_binary_tarball_label() -> None:
    planned = plan_assets("enterprise", "3.30.0", _build(AGENT), OUTPUT, False)
    assert [p.title for p in planned] == ["Masterfiles ready-to-install tarball"]


def test_plan_assets_unexpected_tarball() -> None:
    build = _build(RHEL7, tarballs=["something-else.tar.gz"])
    with pytest.raises(UserError, match="Unexpected tarball"):
        _ = plan_assets("enterprise", "3.30.0", build, OUTPUT, False)


def test_plan_assets_community_vagrant() -> None:
    build = _build(RHEL7, vagrant=True)
    with pytest.raises(UserError, match="no Vagrant quickstart"):
        _ = plan_assets("community", "3.30.0", build, OUTPUT, False)
