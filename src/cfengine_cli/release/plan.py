import re
from dataclasses import dataclass
from pathlib import Path

from cfengine_cli.release.build import Build
from cfengine_cli.release.platforms import get_platform
from cfengine_cli.utils import UserError

S3_URL = "https://cfengine-package-repos.s3.amazonaws.com"
BUILDCACHE_URL = "http://buildcache.cfengine.com/packages/build-in-container"
DOCS_URL = "https://docs.cfengine.com/docs"
PLATFORM_PACKAGE_SUFFIXES = (".deb", ".rpm", ".msi")

ADDITIONAL_ASSETS = "Additional Assets"
# Matches no host, so self-upgrade policy never picks these files
NO_CLASSEXPR = "!any"
NO_ARCH = "no arch"
# The label whose binary tarball is published, as in the legacy release.py
BINARY_TARBALL_LABEL = "PACKAGES_x86_64_linux_redhat_7"
BINARY_TARBALL_FOOTNOTE = (
    "Tarball containing compiled CFEngine host (client) binaries that runs on "
    "most Linux systems but are not optimized for specific library or platform "
    "features. Appropriate for testing purposes. Not supported under the "
    "CFEngine support contract."
)
BINARY_TARBALL_DOCS = "getting-started-installation-general-installation-installation-enterprise-generic-tarball.html"
VAGRANT_DOCS = "getting-started-installation-general-installation-installation-enterprise-vagrant.html"


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
    # packages, "Binary packages" for community packages, and "Additional
    # Assets" for tarballs and the Vagrant quickstart.
    section: str
    # Shown on the downloads page, e.g. "Debian 12" or "Masterfiles source
    # tarball"
    title: str
    # e.g. "x86_64", "aarch64", or "no arch" for tarballs
    arch: str
    # Selects the package in self-upgrade policy, e.g.
    # "!am_policy_hub.debian_12.x86_64"
    classexpr: str
    # Build label the file came from, e.g. "PACKAGES_x86_64_linux_debian_12".
    # None for most additional assets.
    package: str | None
    # Link to installation docs, if any
    instructions: str | None = None
    # Footnote text, if any
    footnote: str | None = None


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


def _docs_url(version: str, page: str) -> str:
    """Return a docs link, e.g. for 3.30.0 under docs/3.30/, for master under docs/master/."""
    docs_version = re.sub(r"(\d+\.\d+).*", r"\1", version)
    return f"{DOCS_URL}/{docs_version}/{page}"


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


def _asset(
    source: Path,
    release_path: str,
    title: str,
    build_name: str,
    output_dir: str,
    debug: bool,
    *,
    name: str | None = None,
    arch: str = NO_ARCH,
    package: str | None = None,
    instructions: str | None = None,
    footnote: str | None = None,
) -> PlannedFile:
    """Plan an additional asset. name is the published file name, if not the source's."""
    destination, url = _place(
        source, release_path, name or source.name, build_name, output_dir, debug
    )
    return PlannedFile(
        source=source,
        destination=destination,
        url=url,
        section=ADDITIONAL_ASSETS,
        title=title,
        arch=arch,
        classexpr=NO_CLASSEXPR,
        package=package,
        instructions=instructions,
        footnote=footnote,
    )


def plan_assets(
    project: str,
    version: str,
    build: Build,
    output_dir: str,
    debug: bool,
) -> list[PlannedFile]:
    """Plan the additional assets: tarballs and the Vagrant quickstart.

    In the same order as the legacy release.py lists them.
    """
    build_name = build.name
    misc = f"{_edition_root(project, version)}/misc"

    # Sort tarballs/ by kind
    masterfiles_packages: list[Path] = []
    masterfiles_sources: list[Path] = []
    sources: list[Path] = []
    for source in build.tarballs.packages:
        if source.name.startswith("cfengine-masterfiles-"):
            if source.name.endswith(".pkg.tar.gz"):
                masterfiles_packages.append(source)
            else:
                masterfiles_sources.append(source)
        elif source.name.startswith("cfengine-3."):
            sources.append(source)
        else:
            raise UserError(f"Unexpected tarball '{source}'")

    planned: list[PlannedFile] = []
    for source in masterfiles_packages:
        planned.append(
            _asset(
                source,
                misc,
                "Masterfiles ready-to-install tarball",
                build_name,
                output_dir,
                debug,
                package="PACKAGES_VIRTUAL_PACKAGES_masterfiles",
            )
        )

    binary_label = build.labels.get(BINARY_TARBALL_LABEL)
    if binary_label is not None:
        for source in binary_label.packages:
            if source.name.endswith(".pkg.tar.gz"):
                planned.append(
                    _asset(
                        source,
                        misc,
                        "Linux binary tarball (unsupported)",
                        build_name,
                        output_dir,
                        debug,
                        arch="x86_64",
                        instructions=_docs_url(version, BINARY_TARBALL_DOCS),
                        footnote=BINARY_TARBALL_FOOTNOTE,
                    )
                )

    if build.vagrant is not None:
        if project == "community":
            raise UserError("Community releases have no Vagrant quickstart")
        for source in build.vagrant.packages:
            planned.append(
                _asset(
                    source,
                    misc,
                    "Vagrant Environment",
                    build_name,
                    output_dir,
                    debug,
                    arch="Linux/Mac/Windows (Virtualbox)",
                    instructions=_docs_url(version, VAGRANT_DOCS),
                )
            )

    # Source tarballs are only published with community releases
    if project == "community":
        for source in sources:
            # cfengine-3.30.0.tar.gz is published as cfengine-community-3.30.0.tar.gz
            planned.append(
                _asset(
                    source,
                    "tarballs",
                    "Source code tarball",
                    build_name,
                    output_dir,
                    debug,
                    name=source.name.replace("cfengine-", "cfengine-community-", 1),
                )
            )
        for source in masterfiles_sources:
            planned.append(
                _asset(
                    source,
                    "tarballs",
                    "Masterfiles source tarball",
                    build_name,
                    output_dir,
                    debug,
                )
            )

    return planned
