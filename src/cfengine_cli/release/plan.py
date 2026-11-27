from dataclasses import dataclass
from pathlib import Path

from cfengine_cli.release.build import Build
from cfengine_cli.release.platforms import get_platform

S3_URL = "https://cfengine-package-repos.s3.amazonaws.com"
BUILDCACHE_URL = "http://buildcache.cfengine.com/packages/build-in-container"
PLATFORM_PACKAGE_SUFFIXES = (".deb", ".rpm", ".msi")


# Arguments must be passed with keywords
@dataclass(frozen=True, kw_only=True)
class PlannedFile:
    """A file to publish, and how it appears in the release metadata."""

    # The file to release, as built. In the build directory, never modified.
    source: Path
    # The published copy of source in the release dir. .rpm and .deb copies are
    # signed.
    # None for debug releases (nightlies): nothing is copied, and the metadata
    # links to the source on buildcache.
    destination: Path | None
    # Download URL in the metadata. For releases, the URL of destination on S3,
    # once uploaded. For debug releases (nightlies), the URL of source on
    # buildcache.
    url: str
    # Artifact section. "Policy Server" and "Hosts (Clients)" for enterprise
    # packages, and "Binary packages" for community packages.
    section: str
    # Shown on the downloads page, e.g. "Debian 12"
    title: str
    # e.g. "x86_64" or "aarch64"
    arch: str
    # Selects the package in self-upgrade policy, e.g.
    # "!am_policy_hub.debian_12.x86_64"
    classexpr: str
    # Build label the file came from, e.g. "PACKAGES_x86_64_linux_debian_12"
    package: str


def _section(project: str, hub: bool) -> str:
    if project == "community":
        return "Binary packages"
    return "Policy Server" if hub else "Hosts (Clients)"


def _edition_root(project: str, version: str) -> str:
    """Return the edition's directory in the release, relative to its root."""
    if project == "community":
        return f"community_binaries/Community-{version}"
    return f"enterprise/Enterprise-{version}"


def _release_path(project: str, version: str, hub: bool, release_dir: str) -> str:
    """Return a platform's directory in the release, relative to its root."""
    if project == "community":
        return f"{_edition_root(project, version)}/{release_dir}"
    role = "hub" if hub else "agent"
    return f"{_edition_root(project, version)}/{role}/{release_dir}"


def _place(
    source: Path,
    release_path: str,
    name: str,
    build_name: str,
    output_dir: str,
    debug: bool,
) -> tuple[Path | None, str]:
    """Return the destination and URL of a file published as name.

    Debug releases (nightlies) link to the source on buildcache, under its own
    name.
    """
    if debug:
        return None, f"{BUILDCACHE_URL}/{build_name}/{source.parent.name}/{source.name}"
    destination = Path(output_dir) / "release" / release_path / name
    return destination, f"{S3_URL}/{release_path}/{name}"


def plan_packages(
    project: str,
    version: str,
    build: Build,
    output_dir: str,
    debug: bool,
) -> list[PlannedFile]:
    """Plan the platform packages, i.e. .deb, .rpm and .msi, of every label."""
    build_name = build.name
    planned: list[PlannedFile] = []
    platforms = {label: get_platform(label, project) for label in build.labels}
    for label in sorted(platforms, key=lambda label: platforms[label].sort_key()):
        platform = platforms[label]
        label_dir = build.labels[label]
        release_path = _release_path(
            project, version, platform.hub, platform.release_dir
        )
        for source in label_dir.packages:
            if not source.name.endswith(PLATFORM_PACKAGE_SUFFIXES):
                continue
            destination, url = _place(
                source, release_path, source.name, build_name, output_dir, debug
            )
            planned.append(
                PlannedFile(
                    source=source,
                    destination=destination,
                    url=url,
                    section=_section(project, platform.hub),
                    title=platform.title,
                    arch=platform.arch,
                    classexpr=platform.classexpr,
                    package=label,
                )
            )
    return planned
