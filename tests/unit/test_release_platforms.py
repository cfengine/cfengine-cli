import pytest

from cfengine_cli.release.platforms import get_platform
from cfengine_cli.utils import UserError

# Every package in the published release-data/<project>/3.29.0.json, made by
# the legacy release.py: label, title, arch, classexpr, release_dir. Except the
# Ubuntu agent titles, which had .04.
ENTERPRISE = [
    ("PACKAGES_HUB_x86_64_linux_debian_12", "Debian 12", "x86_64", "am_policy_hub.debian_12.x86_64", "debian_12_x86_64"),
    ("PACKAGES_HUB_arm_64_linux_debian_12", "Debian 12", "aarch64", "am_policy_hub.debian_12.aarch64", "debian_12_arm_64"),
    ("PACKAGES_HUB_x86_64_linux_debian_13", "Debian 13", "x86_64", "am_policy_hub.debian_13.x86_64", "debian_13_x86_64"),
    ("PACKAGES_HUB_arm_64_linux_debian_13", "Debian 13", "aarch64", "am_policy_hub.debian_13.aarch64", "debian_13_arm_64"),
    ("PACKAGES_HUB_x86_64_linux_redhat_8", "Red Hat / CentOS 8", "x86_64", "am_policy_hub.(redhat_8|centos_8).x86_64", "redhat_8_x86_64"),
    ("PACKAGES_HUB_x86_64_linux_redhat_9", "Red Hat 9", "x86_64", "am_policy_hub.redhat_9.x86_64", "redhat_9_x86_64"),
    ("PACKAGES_HUB_x86_64_linux_redhat_10", "Red Hat 10", "x86_64", "am_policy_hub.redhat_10.x86_64", "redhat_10_x86_64"),
    ("PACKAGES_HUB_arm_64_linux_redhat_10", "Red Hat 10", "aarch64", "am_policy_hub.redhat_10.aarch64", "redhat_10_arm_64"),
    ("PACKAGES_HUB_x86_64_linux_ubuntu_22", "Ubuntu 22", "x86_64", "am_policy_hub.ubuntu_22.x86_64", "ubuntu_22_x86_64"),
    ("PACKAGES_HUB_arm_64_linux_ubuntu_22", "Ubuntu 22", "aarch64", "am_policy_hub.ubuntu_22.aarch64", "ubuntu_22_arm_64"),
    ("PACKAGES_HUB_x86_64_linux_ubuntu_24", "Ubuntu 24", "x86_64", "am_policy_hub.ubuntu_24.x86_64", "ubuntu_24_x86_64"),
    ("PACKAGES_HUB_arm_64_linux_ubuntu_24", "Ubuntu 24", "aarch64", "am_policy_hub.ubuntu_24.aarch64", "ubuntu_24_arm_64"),
    ("PACKAGES_HUB_x86_64_linux_ubuntu_26", "Ubuntu 26", "x86_64", "am_policy_hub.ubuntu_26.x86_64", "ubuntu_26_x86_64"),
    ("PACKAGES_HUB_arm_64_linux_ubuntu_26", "Ubuntu 26", "aarch64", "am_policy_hub.ubuntu_26.aarch64", "ubuntu_26_arm_64"),
    ("PACKAGES_x86_64_linux_debian_12", "Debian 12", "x86_64", "!am_policy_hub.debian_12.x86_64", "agent_debian12_x86_64"),
    ("PACKAGES_arm_64_linux_debian_12", "Debian 12", "aarch64", "!am_policy_hub.debian_12.aarch64", "agent_debian12_arm_64"),
    ("PACKAGES_x86_64_linux_debian_13", "Debian 13", "x86_64", "!am_policy_hub.debian_13.x86_64", "agent_debian13_x86_64"),
    ("PACKAGES_arm_64_linux_debian_13", "Debian 13", "aarch64", "!am_policy_hub.debian_13.aarch64", "agent_debian13_arm_64"),
    ("PACKAGES_x86_64_linux_ubuntu_20", "Ubuntu 20", "x86_64", "!am_policy_hub.ubuntu_20.x86_64", "agent_ubuntu20_x86_64"),
    ("PACKAGES_x86_64_linux_ubuntu_22", "Ubuntu 22", "x86_64", "!am_policy_hub.ubuntu_22.x86_64", "agent_ubuntu22_x86_64"),
    ("PACKAGES_arm_64_linux_ubuntu_22", "Ubuntu 22", "aarch64", "!am_policy_hub.ubuntu_22.aarch64", "agent_ubuntu22_arm_64"),
    ("PACKAGES_arm_64_linux_ubuntu_24", "Ubuntu 24", "aarch64", "!am_policy_hub.ubuntu_24.aarch64", "agent_ubuntu24_arm_64"),
    ("PACKAGES_x86_64_linux_ubuntu_24", "Ubuntu 24", "x86_64", "!am_policy_hub.ubuntu_24.x86_64", "agent_ubuntu24_x86_64"),
    ("PACKAGES_arm_64_linux_ubuntu_26", "Ubuntu 26", "aarch64", "!am_policy_hub.ubuntu_26.aarch64", "agent_ubuntu26_arm_64"),
    ("PACKAGES_x86_64_linux_ubuntu_26", "Ubuntu 26", "x86_64", "!am_policy_hub.ubuntu_26.x86_64", "agent_ubuntu26_x86_64"),
    ("PACKAGES_x86_64_linux_redhat_7", "Red Hat / CentOS 7", "x86_64", "!am_policy_hub.(redhat_7|centos_7).x86_64", "agent_rhel7_x86_64"),
    ("PACKAGES_x86_64_linux_redhat_8", "Red Hat / CentOS 8.1", "x86_64", "!am_policy_hub.(redhat_8|centos_8).x86_64", "agent_rhel8_x86_64"),
    ("PACKAGES_arm_64_linux_redhat_8", "Red Hat / CentOS 8.1", "aarch64", "!am_policy_hub.(redhat_8|centos_8).aarch64", "agent_rhel8_arm_64"),
    ("PACKAGES_x86_64_linux_redhat_9", "Red Hat / CentOS 9", "x86_64", "!am_policy_hub.(redhat_9|centos_9).x86_64", "agent_rhel9_x86_64"),
    ("PACKAGES_arm_64_linux_redhat_9", "Red Hat / CentOS 9", "aarch64", "!am_policy_hub.(redhat_9|centos_9).aarch64", "agent_rhel9_arm_64"),
    ("PACKAGES_x86_64_linux_redhat_10", "Red Hat / CentOS 10", "x86_64", "!am_policy_hub.(redhat_10|centos_10).x86_64", "agent_rhel10_x86_64"),
    ("PACKAGES_arm_64_linux_redhat_10", "Red Hat / CentOS 10", "aarch64", "!am_policy_hub.(redhat_10|centos_10).aarch64", "agent_rhel10_arm_64"),
    ("PACKAGES_x86_64_mingw", "Windows Server 2012", "x86_64", "!am_policy_hub.windows.x86_64", "windows_x86_64"),
]  # fmt: skip

COMMUNITY = [
    ("PACKAGES_x86_64_linux_debian_12", "Debian 12", "x86_64", "debian_12.x86_64", "agent_debian12_x86_64"),
    ("PACKAGES_arm_64_linux_debian_12", "Debian 12", "aarch64", "debian_12.aarch64", "agent_debian12_arm_64"),
    ("PACKAGES_x86_64_linux_debian_13", "Debian 13", "x86_64", "debian_13.x86_64", "agent_debian13_x86_64"),
    ("PACKAGES_arm_64_linux_debian_13", "Debian 13", "aarch64", "debian_13.aarch64", "agent_debian13_arm_64"),
    ("PACKAGES_x86_64_linux_ubuntu_20", "Ubuntu 20", "x86_64", "ubuntu_20.x86_64", "agent_ubuntu20_x86_64"),
    ("PACKAGES_x86_64_linux_ubuntu_22", "Ubuntu 22", "x86_64", "ubuntu_22.x86_64", "agent_ubuntu22_x86_64"),
    ("PACKAGES_arm_64_linux_ubuntu_22", "Ubuntu 22", "aarch64", "ubuntu_22.aarch64", "agent_ubuntu22_arm_64"),
    ("PACKAGES_arm_64_linux_ubuntu_24", "Ubuntu 24", "aarch64", "ubuntu_24.aarch64", "agent_ubuntu24_arm_64"),
    ("PACKAGES_x86_64_linux_ubuntu_24", "Ubuntu 24", "x86_64", "ubuntu_24.x86_64", "agent_ubuntu24_x86_64"),
    ("PACKAGES_arm_64_linux_ubuntu_26", "Ubuntu 26", "aarch64", "ubuntu_26.aarch64", "agent_ubuntu26_arm_64"),
    ("PACKAGES_x86_64_linux_ubuntu_26", "Ubuntu 26", "x86_64", "ubuntu_26.x86_64", "agent_ubuntu26_x86_64"),
    ("PACKAGES_x86_64_linux_redhat_7", "Red Hat / CentOS 7", "x86_64", "(redhat_7|centos_7).x86_64", "agent_rhel7_x86_64"),
    ("PACKAGES_x86_64_linux_redhat_8", "Red Hat / CentOS 8", "x86_64", "(redhat_8|centos_8).x86_64", "agent_rhel8_x86_64"),
    ("PACKAGES_arm_64_linux_redhat_8", "Red Hat / CentOS 8", "aarch64", "(redhat_8|centos_8).aarch64", "agent_rhel8_arm_64"),
    ("PACKAGES_x86_64_linux_redhat_9", "Red Hat / CentOS 9", "x86_64", "(redhat_9|centos_9).x86_64", "agent_rhel9_x86_64"),
    ("PACKAGES_arm_64_linux_redhat_9", "Red Hat / CentOS 9", "aarch64", "(redhat_9|centos_9).aarch64", "agent_rhel9_arm_64"),
    ("PACKAGES_x86_64_linux_redhat_10", "Red Hat / CentOS 10", "x86_64", "(redhat_10|centos_10).x86_64", "agent_rhel10_x86_64"),
    ("PACKAGES_arm_64_linux_redhat_10", "Red Hat / CentOS 10", "aarch64", "(redhat_10|centos_10).aarch64", "agent_rhel10_arm_64"),
]  # fmt: skip


@pytest.mark.parametrize(
    "project, label, title, arch, classexpr, release_dir",
    [("enterprise", *row) for row in ENTERPRISE]
    + [("community", *row) for row in COMMUNITY],
)
def test_get_platform_matches_published(
    project: str, label: str, title: str, arch: str, classexpr: str, release_dir: str
) -> None:
    hub = label.startswith("PACKAGES_HUB_")
    platform = get_platform(label, project)
    published = (hub, title, arch, classexpr, release_dir)
    assert (
        platform.hub,
        platform.title,
        platform.arch,
        platform.classexpr,
        platform.release_dir,
    ) == published


def test_platform_sort_key() -> None:
    expected = [
        "PACKAGES_HUB_x86_64_linux_debian_12",
        "PACKAGES_HUB_x86_64_linux_ubuntu_22",
        "PACKAGES_HUB_x86_64_linux_redhat_9",
        "PACKAGES_x86_64_linux_debian_12",
        "PACKAGES_arm_64_linux_debian_12",
        "PACKAGES_x86_64_linux_ubuntu_24",
        "PACKAGES_arm_64_linux_ubuntu_24",
        "PACKAGES_x86_64_linux_redhat_8",
        "PACKAGES_x86_64_linux_redhat_10",
        "PACKAGES_arm_64_linux_redhat_10",
        "PACKAGES_x86_64_mingw",
    ]
    labels = sorted(expected, reverse=True)
    labels.sort(key=lambda label: get_platform(label, "enterprise").sort_key())
    assert labels == expected


@pytest.mark.parametrize(
    "label",
    [
        "PACKAGES_x86_64_freebsd_14",
        "PACKAGES_x86_64_linux_suse_15",
        "PACKAGES_i386_linux_debian_12",
    ],
)
def test_get_platform_unknown_label(label: str) -> None:
    with pytest.raises(UserError, match=f"Unknown build label '{label}'"):
        _ = get_platform(label, "enterprise")


def test_get_platform_community_hub() -> None:
    with pytest.raises(UserError, match="no hub packages"):
        _ = get_platform("PACKAGES_HUB_x86_64_linux_debian_12", "community")


def test_get_platform_community_windows() -> None:
    with pytest.raises(UserError, match="no Windows packages"):
        _ = get_platform("PACKAGES_x86_64_mingw", "community")
