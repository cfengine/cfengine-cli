from pathlib import Path

from cfengine_cli.release.build import Build, PackageDir
from cfengine_cli.release.plan import PlannedFile, plan_packages

BUILD = Path("/builds/jenkins-master-nightly-pipeline-123")
OUTPUT = "/var/www/buildcache"
HUB = "PACKAGES_HUB_x86_64_linux_debian_12"
AGENT = "PACKAGES_x86_64_linux_redhat_9"
RHEL7 = "PACKAGES_x86_64_linux_redhat_7"
WINDOWS = "PACKAGES_x86_64_mingw"
S3 = "https://cfengine-package-repos.s3.amazonaws.com"

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
