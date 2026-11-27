import copy
import datetime
import re
from typing import Required, TypedDict

RELEASE_DATA_URL = "https://cfengine-package-repos.s3.amazonaws.com/release-data"


class LtsBranch(TypedDict):
    """An entry in lts_branches in releases.json."""

    branch_name: str  # e.g. 3.27.x, or nightly-3.27.x for community nightlies
    supported_until: str  # YYYY-MM


class Release(TypedDict, total=False):
    """An entry in releases in releases.json. Old entries lack some keys."""

    version: Required[str]  # e.g. 3.27.0, or 3.27.x / master for nightlies
    URL: str  # Of release-data/<project>/<version>.json.
    debug: bool  # Nightly, hidden from downloads and from the latest flags
    release_date: str  # YYYY-MM-DD, or "nightly"
    lts_branch: str  # branch_name of the LTS branch it belongs to
    alpha: bool  # Legacy, only on old entries
    beta: bool  # Legacy, only on old entries like 3.15.0b1
    latest: bool  # Newest non-debug release
    latest_stable: bool  # Newest non-debug release that is not a beta
    latest_on_branch: bool  # Newest stable release on its LTS branch
    latestLTS: bool  # latest_on_branch of the newest LTS branch


class ReleasesData(TypedDict):
    """The contents of releases.json."""

    lts_branches: list[LtsBranch]
    releases: list[Release]


class Artifact(TypedDict, total=False):
    """A downloadable file in release-data/<project>/<version>.json."""

    Title: Required[str]  # e.g. Debian 12
    Arch: Required[str]  # e.g. x86_64, or "no arch"
    classexpr: Required[str]  # Selects the package in self-upgrade policy
    Published: Required[bool]  # False hides it from the downloads page
    URL: Required[str]  # cf-remote reads "URL"
    SHA256: Required[str]
    package: str  # Build label, e.g. PACKAGES_x86_64_linux_debian_12
    Footnote: int  # 1-based index into footnotes
    Instructions: str  # Link to installation docs


class VersionDocument(TypedDict, total=False):
    """The contents of release-data/<project>/<version>.json."""

    project: Required[str]
    version: Required[str]  # The title, from version_title()
    nightly_release_date: str  # Only for nightlies
    note: str  # Only for non-LTS versions
    # Always set, but not Required, so version_document() can add them after
    # the optional keys. The key order matters, see version_document().
    # Section title, e.g. "Policy Server", mapped to its artifacts
    artifacts: dict[str, list[Artifact]]
    footnotes: list[str]


NON_LTS_NOTE = (
    'Please note that <a href="/supported-versions/">non-LTS releases are '
    "unsupported</a>, i.e. excluded from CFEngine Enterprise support "
    "contract, and we do not recommend installing them in production."
)


def is_nightly(version: str) -> bool:
    """Return True for master and LTS branches like 3.30.x."""
    return version == "master" or version.endswith(".x")


def release_branch(project: str, version: str) -> str:
    """Return the branch of a version in releases.json.

    A version number like 3.30.0 becomes 3.30.x.
    Community master becomes nightly-master.
    """
    if not is_nightly(version):
        return re.sub(r"\.\d+$", ".x", version)
    if project == "community":
        return f"nightly-{version}"
    return version


def release_data_url(project: str, version: str) -> str:
    """Return the URL of release-data/<project>/<version>.json."""
    return f"{RELEASE_DATA_URL}/{project}/{version}.json"


def version_key(version: str) -> tuple[int, ...]:
    """Sort key for versions in releases.json.

    master > 3.30.x > 3.30.0 > 3.27.0 > 3.15.0 > 3.15.0b1. We no longer
    release betas, but releases.json still has old ones like 3.15.0b1.
    """
    if version == "master":
        return (999,)
    match = re.fullmatch(r"(\d+(?:\.\d+)*)(.*)", version)
    if not match:
        return (0,)
    parts = [int(x) for x in match.group(1).split(".")]
    remainder = match.group(2)
    if remainder == ".x":
        # A branch nightly sorts above every release on its branch
        parts.append(999)
        suffix = (2, 0)
    elif remainder == "":
        suffix = (2, 0)
    elif remainder.startswith("b"):
        suffix = (1, int(remainder[1:]))
    elif remainder.startswith("a"):
        suffix = (0, int(remainder[1:]))
    else:
        suffix = (0, 0)
    return tuple(parts) + suffix


def _minor(version: str) -> int:
    """Return the minor version, e.g. 30 for 3.30.0, or 0 for master."""
    match = re.match(r"\d+\.(\d+)", version)
    return int(match.group(1)) if match else 0


def is_lts(version: str) -> bool:
    """Return True if the version is on an LTS branch, e.g. 3.27.x or 3.30.x."""
    minor = _minor(version)
    if minor < 11:
        return minor % 3 == 1  # 3.7, 3.10
    return minor % 3 == 0  # 3.12, 3.15, ...


def support_end(version: str) -> tuple[str, str]:
    """Return when the version's branch goes out of support.

    E.g. ("2028-12", "December 2028") for 3.27.x.
    """
    # Same formula as the legacy release.py in the infra repo. LTS branches
    # come 1.5 years apart, so their support ends alternate between December
    # of one year and August of the next. The value below is a year as a
    # decimal number. (minor + 1) / 2 is a whole number or ends in .5, so
    # adding 2014.4 makes it end in .4 or .9. Rounding then gives the year:
    # .4 rounds down and means December, .9 rounds up and means August.
    # E.g. 3.27: 2028.4 -> December 2028, 3.30: 2029.9 -> August 2030.
    minor = _minor(version)
    if minor < 11:
        value = minor / 2 + 2014.4
    else:
        value = (minor + 1) / 2 + 2014.4
    year = round(value)
    if value - year > 0.2:
        return f"{year}-12", f"December {year}"
    return f"{year}-08", f"August {year}"


def version_title(project: str, version: str) -> str:
    """Return the title shown for a version.

    E.g. "3.27.0 LTS (supported until December 2028)" for enterprise.
    """
    enterprise = project == "enterprise"
    if is_lts(version):
        title = f"{version} LTS"
        if enterprise:
            _, until = support_end(version)
            title += f" (supported until {until})"
        return title
    title = f"{version} non-LTS"
    if enterprise:
        title += " (unsupported)"
    return title


def update_releases(
    releases_data: ReleasesData,
    project: str,
    version: str,
    branch: str,
    debug: bool,
    today: datetime.date,
) -> ReleasesData:
    """Returns a copy of releases.json with the version added and the latest flags redone."""
    data = copy.deepcopy(releases_data)
    branches = data["lts_branches"]

    releases = _without_version(data["releases"], version)
    release = _new_release(project, version, debug, today)
    releases.append(release)

    if _in_lts_branches(version, branch):
        _attach_to_branch(release, branches, branch)

    releases.sort(key=lambda r: version_key(r["version"]), reverse=True)
    _clear_latest_flags(releases)
    _set_latest_flags(releases, branches)

    return {"lts_branches": branches, "releases": releases}


def _in_lts_branches(version: str, branch: str) -> bool:
    """Return True if the release is listed under a branch in lts_branches.

    That is LTS versions, and community master nightlies. master is not LTS,
    but the legacy release.py has always listed it under the nightly-master
    branch, which makes "cf-remote install --version nightly-master" work.
    """
    return is_lts(version) or branch == "nightly-master"


def _without_version(releases: list[Release], version: str) -> list[Release]:
    """Drop any existing entry for the version, so re-releasing does not become a duplicate entry."""
    return [r for r in releases if r["version"] != version]


def _new_release(
    project: str, version: str, debug: bool, today: datetime.date
) -> Release:
    return {
        "version": version,
        "URL": release_data_url(project, version),
        "debug": debug,
        "release_date": "nightly" if is_nightly(version) else str(today),
    }


def _attach_to_branch(release: Release, branches: list[LtsBranch], branch: str) -> None:
    """Attach the release to its branch.

    So cf-remote can expire it, and the per-branch flags can find it.
    """
    release["lts_branch"] = branch
    # Add the branch the first time a release is made on it. Newest first,
    # as _set_branch_flags expects.
    if not any(b["branch_name"] == branch for b in branches):
        date, _ = support_end(release["version"])
        branches.insert(0, {"branch_name": branch, "supported_until": date})


def _clear_latest_flags(releases: list[Release]) -> None:
    """Drop existing latest flags so they can be recomputed."""
    for release in releases:
        _ = release.pop("latest", None)
        _ = release.pop("latest_stable", None)
        _ = release.pop("latest_on_branch", None)
        _ = release.pop("latestLTS", None)


def _set_latest_flags(releases: list[Release], branches: list[LtsBranch]) -> None:
    """Set the latest flags. releases must be sorted newest first."""
    # Nightlies are debug releases and never get the latest flags. Only the
    # first, i.e. newest, entry gets the flag.
    published = [r for r in releases if not r.get("debug")]
    if published:
        published[0]["latest"] = True

    # Skip old betas like 3.15.0b1
    stable = [r for r in published if "b" not in r["version"]]
    if stable:
        stable[0]["latest_stable"] = True

    _set_branch_flags(stable, branches)


def _set_branch_flags(stable: list[Release], branches: list[LtsBranch]) -> None:
    """Mark the newest stable release on each branch.

    lts_branches is newest first, so the first branch with a stable release
    also holds the latest LTS release. cf-remote uses latestLTS as its
    default version.
    """
    found_latest_lts = False
    for b in branches:
        on_branch = [r for r in stable if r.get("lts_branch") == b["branch_name"]]
        if not on_branch:
            continue
        on_branch[0]["latest_on_branch"] = True
        if not found_latest_lts:
            on_branch[0]["latestLTS"] = True
            found_latest_lts = True


def version_document(
    project: str,
    version: str,
    branch: str,
    artifacts: dict[str, list[Artifact]],
    footnotes: list[str],
    today: datetime.date,
) -> VersionDocument:
    """Return the contents of release-data/<project>/<version>.json."""
    # Built in the key order of the legacy release.py, with the optional keys
    # before the artifacts
    doc: VersionDocument = {
        "project": project,
        "version": version_title(project, version),
    }
    if is_nightly(version):
        doc["nightly_release_date"] = str(today)
    # Same as the legacy release.py: no note for releases in lts_branches. So
    # community master nightlies have no note, while enterprise ones do.
    if not _in_lts_branches(version, branch):
        doc["note"] = NON_LTS_NOTE
    doc["artifacts"] = artifacts
    doc["footnotes"] = footnotes
    return doc
