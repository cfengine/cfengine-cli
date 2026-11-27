import re
from dataclasses import dataclass

from cfengine_cli.utils import UserError

_ARCHES = {"x86_64": "x86_64", "arm_64": "aarch64"}
_OS_TITLES = {"debian": "Debian", "ubuntu": "Ubuntu", "redhat": "Red Hat / CentOS"}
_OS_ORDER = ("debian", "ubuntu", "redhat", "windows")

# e.g. PACKAGES_HUB_x86_64_linux_debian_12 or PACKAGES_arm_64_linux_redhat_9,
# with a known arch and OS
_LABEL_RE = re.compile(
    rf"PACKAGES_(HUB_)?({'|'.join(_ARCHES)})_linux_({'|'.join(_OS_TITLES)})_(\d+)"
)
_WINDOWS_LABEL = "PACKAGES_x86_64_mingw"


@dataclass(frozen=True)
class Platform:
    """How a build label's packages appear in a release.

    The values match the 3.29.0 release made by the legacy release.py in the
    infra repo, except the Ubuntu agent titles, which had .04. Self-upgrade
    policy uses classexpr to pick packages, so changing it changes which hosts
    get which package.
    """

    hub: bool
    title: str  # e.g. Debian 12
    arch: str  # x86_64 or aarch64
    classexpr: str  # e.g. !am_policy_hub.debian_12.x86_64
    release_dir: str  # Subdirectory in the published release, e.g. agent_rhel8_x86_64
    os: str  # debian, ubuntu, redhat or windows
    version: int  # e.g. 12, or 2012 for Windows Server 2012

    def sort_key(self) -> tuple[bool, int, int, bool]:
        """Order on the downloads page.

        Hubs, then agents. Then by OS and version, with x86_64 before
        aarch64. The legacy release.py in infra uses the same order.
        """
        return (
            not self.hub,
            _OS_ORDER.index(self.os),
            self.version,
            self.arch != "x86_64",
        )


def _limit_to_role(project: str, hub: bool, classexpr: str) -> str:
    """Limit a classexpr to hubs or to non-hubs, where needed."""
    if project == "community":
        # Community has one package for both hubs and agents
        if hub:
            raise UserError("Community releases have no hub packages")
        return classexpr

    # Enterprise has separate hub and agent packages
    return f"am_policy_hub.{classexpr}" if hub else f"!am_policy_hub.{classexpr}"


def _includes_centos(os: str, version: int, hub: bool) -> bool:
    # Exception: RHEL hubs from 9 on are for Red Hat only
    # TODO: Figure out if this is necessary
    return os == "redhat" and not (hub and version >= 9)


def _title(project: str, os: str, version: int, hub: bool) -> str:
    if (os == "redhat") and (not _includes_centos(os, version, hub)):
        return f"Red Hat {version}"
    title = f"{_OS_TITLES[os]} {version}"
    # Exception: enterprise says 8.1 for RHEL 8 agents
    if (os == "redhat") and (version == 8) and (not hub) and (project == "enterprise"):
        title += ".1"
    return title


def get_platform(label: str, project: str) -> Platform:
    """Return how a build label's packages appear in a project's release."""
    if label == _WINDOWS_LABEL:
        # Windows packages are enterprise only, and there are no Windows hubs
        if project == "community":
            raise UserError("Community releases have no Windows packages")
        return Platform(
            False,
            "Windows Server 2012",
            "x86_64",
            "!am_policy_hub.windows.x86_64",
            "windows_x86_64",
            "windows",
            2012,
        )

    match = _LABEL_RE.fullmatch(label)
    if not match:
        raise UserError(f"Unknown build label '{label}'")
    hub = match.group(1) is not None
    label_arch, os, version = match.group(2), match.group(3), int(match.group(4))
    arch = _ARCHES[label_arch]

    if _includes_centos(os, version, hub):
        classexpr = f"(redhat_{version}|centos_{version}).{arch}"
    else:
        classexpr = f"{os}_{version}.{arch}"

    if hub:
        release_dir = f"{os}_{version}_{label_arch}"
    else:
        short = "rhel" if os == "redhat" else os
        release_dir = f"agent_{short}{version}_{label_arch}"

    return Platform(
        hub,
        _title(project, os, version, hub),
        arch,
        _limit_to_role(project, hub, classexpr),
        release_dir,
        os,
        version,
    )
