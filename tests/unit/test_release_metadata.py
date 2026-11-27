import copy
import datetime

import pytest

from cfengine_cli.release.metadata import (
    NON_LTS_NOTE,
    Release,
    ReleasesData,
    is_lts,
    release_branch,
    support_end,
    update_releases,
    version_document,
    version_key,
    version_title,
)

# Every version in the published enterprise releases.json, highest first
EXPECTED = [
    "master", "3.27.x", "3.27.0", "3.26.0", "3.25.0", "3.24.x",
    "3.24.3", "3.24.2", "3.24.1", "3.24.0", "3.23.0", "3.22.0",
    "3.21.x", "3.21.8", "3.21.7", "3.21.6", "3.21.5", "3.21.4",
    "3.21.3", "3.21.2", "3.21.1", "3.21.0", "3.20.0", "3.19.0",
    "3.18.x", "3.18.8", "3.18.7", "3.18.6", "3.18.5", "3.18.4",
    "3.18.3", "3.18.2", "3.18.1", "3.18.0", "3.17.0", "3.16.0",
    "3.15.x", "3.15.7", "3.15.6", "3.15.5", "3.15.4", "3.15.3",
    "3.15.2", "3.15.1", "3.15.0", "3.15.0b1", "3.14.0", "3.13.0",
    "3.12.x", "3.12.7", "3.12.6", "3.12.5", "3.12.4", "3.12.3",
    "3.12.2", "3.12.1", "3.12.0", "3.11.0", "3.11.0b1", "3.10.x",
    "3.10.7", "3.10.6", "3.10.5", "3.10.4", "3.10.3", "3.10.2",
    "3.10.1", "3.10.0", "3.9.2", "3.9.0", "3.9.0b1", "3.8.2",
    "3.8.1", "3.8.0", "3.8.0b1", "3.7.8", "3.7.7", "3.7.6",
    "3.7.5", "3.7.4", "3.7.3", "3.7.2", "3.7.1", "3.7.0",
    "3.6.7", "3.6.6", "3.6.5", "3.6.4", "3.6.3", "3.6.2",
    "3.6.1", "3.6.0",
]  # fmt: skip


def test_version_key_stable_releases() -> None:
    assert version_key("3.24.0") > version_key("3.9.2")
    assert version_key("3.10.0") > version_key("3.9.2")
    assert version_key("3.27.0") > version_key("3.24.3")


def test_version_key_pre_releases() -> None:
    assert version_key("3.15.0") > version_key("3.15.0b1")
    assert version_key("3.15.0b1") > version_key("3.15.0a1")
    assert version_key("3.15.0b1") > version_key("3.15.0a2")
    assert version_key("3.15.0b2") > version_key("3.15.0b1")


def test_version_key_branch_nightlies() -> None:
    assert version_key("3.27.x") > version_key("3.27.0")
    assert version_key("3.27.x") > version_key("3.24.x")
    assert version_key("3.30.0") > version_key("3.27.x")


def test_version_key_master() -> None:
    assert version_key("master") > version_key("3.30.x")


def test_version_key_unknown() -> None:
    assert version_key("unknown") < version_key("3.6.0")


def test_version_key_sort_order() -> None:
    # Sorting as strings scrambles the order, e.g. 3.10.0 before 3.9.2
    assert sorted(sorted(EXPECTED), key=version_key, reverse=True) == EXPECTED


@pytest.mark.parametrize(
    "version", ["3.7.0", "3.10.0", "3.12.0", "3.24.3", "3.27.0", "3.30.0", "3.30.x"]
)
def test_is_lts(version: str) -> None:
    assert is_lts(version)


@pytest.mark.parametrize(
    "version", ["3.8.0", "3.11.0", "3.26.0", "3.28.0", "3.29.0", "3.31.0", "master"]
)
def test_is_not_lts(version: str) -> None:
    assert not is_lts(version)


# supported_until of each LTS branch in the published enterprise releases.json,
# plus 3.30.x
@pytest.mark.parametrize(
    "version, date",
    [
        ("3.7.x", "2018-08"),
        ("3.10.x", "2019-12"),
        ("3.12.x", "2021-08"),
        ("3.15.x", "2022-12"),
        ("3.18.x", "2024-08"),
        ("3.21.x", "2025-12"),
        ("3.24.x", "2027-08"),
        ("3.27.x", "2028-12"),
        ("3.30.x", "2030-08"),
    ],
)
def test_support_end_date(version: str, date: str) -> None:
    assert support_end(version)[0] == date


def test_support_end_text() -> None:
    assert support_end("3.27.0") == ("2028-12", "December 2028")
    assert support_end("3.30.0") == ("2030-08", "August 2030")


# The first 8 are from the published release-data/<project>/<version>.json
@pytest.mark.parametrize(
    "project, version, title",
    [
        ("enterprise", "master", "master non-LTS (unsupported)"),
        ("enterprise", "3.27.x", "3.27.x LTS (supported until December 2028)"),
        ("enterprise", "3.27.0", "3.27.0 LTS (supported until December 2028)"),
        ("enterprise", "3.26.0", "3.26.0 non-LTS (unsupported)"),
        ("community", "master", "master non-LTS"),
        ("community", "3.27.x", "3.27.x LTS"),
        ("community", "3.27.0", "3.27.0 LTS"),
        ("community", "3.26.0", "3.26.0 non-LTS"),
        ("enterprise", "3.30.0", "3.30.0 LTS (supported until August 2030)"),
        ("enterprise", "3.31.0", "3.31.0 non-LTS (unsupported)"),
    ],
)
def test_version_title(project: str, version: str, title: str) -> None:
    assert version_title(project, version) == title


TODAY = datetime.date(2027, 6, 1)


@pytest.fixture
def releases_data() -> ReleasesData:
    """A small releases.json, shaped like the published enterprise one."""
    return {
        "lts_branches": [
            {"branch_name": "3.27.x", "supported_until": "2028-12"},
            {"branch_name": "3.24.x", "supported_until": "2027-08"},
        ],
        "releases": [
            Release(version="master", debug=True, release_date="nightly", alpha=True),
            Release(version="3.29.0", debug=False, latest=True, latest_stable=True),
            Release(
                version="3.27.x",
                debug=True,
                release_date="nightly",
                lts_branch="3.27.x",
            ),
            Release(
                version="3.27.3",
                debug=False,
                lts_branch="3.27.x",
                latest_on_branch=True,
                latestLTS=True,
            ),
            Release(
                version="3.24.6",
                debug=False,
                lts_branch="3.24.x",
                latest_on_branch=True,
            ),
            Release(version="3.15.0b1", debug=False, beta=True),
        ],
    }


def _flags(data: ReleasesData) -> dict[str, list[str]]:
    """Return which versions have which latest flags."""
    flags = ("latest", "latest_stable", "latest_on_branch", "latestLTS")
    return {
        f: [r["version"] for r in data["releases"] if dict(r).get(f)] for f in flags
    }


def _entry(data: ReleasesData, version: str) -> Release:
    return next(r for r in data["releases"] if r["version"] == version)


def test_update_releases_lts(releases_data: ReleasesData) -> None:
    data = update_releases(
        releases_data, "enterprise", "3.30.0", "3.30.x", False, TODAY
    )
    assert _entry(data, "3.30.0") == {
        "version": "3.30.0",
        "URL": "https://cfengine-package-repos.s3.amazonaws.com/release-data/enterprise/3.30.0.json",
        "debug": False,
        "release_date": "2027-06-01",
        "lts_branch": "3.30.x",
        "latest": True,
        "latest_stable": True,
        "latest_on_branch": True,
        "latestLTS": True,
    }
    assert data["lts_branches"][0] == {
        "branch_name": "3.30.x",
        "supported_until": "2030-08",
    }
    assert _flags(data) == {
        "latest": ["3.30.0"],
        "latest_stable": ["3.30.0"],
        "latest_on_branch": ["3.30.0", "3.27.3", "3.24.6"],
        "latestLTS": ["3.30.0"],
    }


def test_update_releases_non_lts(releases_data: ReleasesData) -> None:
    data = update_releases(
        releases_data, "enterprise", "3.31.0", "3.31.x", False, TODAY
    )
    assert "lts_branch" not in _entry(data, "3.31.0")
    assert len(data["lts_branches"]) == 2
    assert _flags(data) == {
        "latest": ["3.31.0"],
        "latest_stable": ["3.31.0"],
        "latest_on_branch": ["3.27.3", "3.24.6"],
        "latestLTS": ["3.27.3"],
    }


def test_update_releases_enterprise_master(releases_data: ReleasesData) -> None:
    data = update_releases(releases_data, "enterprise", "master", "master", True, TODAY)
    # No "alpha": the legacy release.py set it only because "master" contains
    # an "a"
    assert _entry(data, "master") == {
        "version": "master",
        "URL": "https://cfengine-package-repos.s3.amazonaws.com/release-data/enterprise/master.json",
        "debug": True,
        "release_date": "nightly",
    }
    assert data["releases"][0]["version"] == "master"
    assert _flags(data) == _flags(releases_data)


def test_update_releases_community_master(releases_data: ReleasesData) -> None:
    data = update_releases(
        releases_data, "community", "master", "nightly-master", True, TODAY
    )
    assert _entry(data, "master").get("lts_branch") == "nightly-master"
    assert data["lts_branches"][0]["branch_name"] == "nightly-master"


def test_update_releases_replaces_existing(releases_data: ReleasesData) -> None:
    data = update_releases(
        releases_data, "enterprise", "3.27.3", "3.27.x", False, TODAY
    )
    assert [r["version"] for r in data["releases"]].count("3.27.3") == 1
    assert _entry(data, "3.27.3").get("release_date") == "2027-06-01"


def test_update_releases_skips_old_beta(releases_data: ReleasesData) -> None:
    for release in releases_data["releases"]:
        if release["version"] != "3.15.0b1":
            release["debug"] = True
    data = update_releases(releases_data, "enterprise", "master", "master", True, TODAY)
    assert _flags(data)["latest"] == ["3.15.0b1"]
    assert _flags(data)["latest_stable"] == []


def test_update_releases_does_not_modify_input(releases_data: ReleasesData) -> None:
    original = copy.deepcopy(releases_data)
    _ = update_releases(releases_data, "enterprise", "3.30.0", "3.30.x", False, TODAY)
    assert releases_data == original


def test_version_document() -> None:
    doc = version_document("enterprise", "3.30.0", "3.30.x", {}, ["A footnote"], TODAY)
    assert doc == {
        "project": "enterprise",
        "version": "3.30.0 LTS (supported until August 2030)",
        "artifacts": {},
        "footnotes": ["A footnote"],
    }


@pytest.mark.parametrize(
    "project, version, branch, keys",
    [
        ("enterprise", "3.30.0", "3.30.x", []),
        ("enterprise", "3.31.0", "3.31.x", ["note"]),
        ("enterprise", "master", "master", ["nightly_release_date", "note"]),
        ("community", "master", "nightly-master", ["nightly_release_date"]),
        ("community", "3.30.x", "nightly-3.30.x", ["nightly_release_date"]),
    ],
)
def test_version_document_keys(
    project: str, version: str, branch: str, keys: list[str]
) -> None:
    doc = version_document(project, version, branch, {}, [], TODAY)
    # In the key order of the legacy release.py
    assert list(doc) == ["project", "version", *keys, "artifacts", "footnotes"]
    if "nightly_release_date" in keys:
        assert doc.get("nightly_release_date") == "2027-06-01"
    if "note" in keys:
        assert doc.get("note") == NON_LTS_NOTE


@pytest.mark.parametrize(
    "project, version, branch",
    [
        ("community", "3.30.0", "3.30.x"),
        ("enterprise", "3.30.0", "3.30.x"),
        # Nightlies, as in the published releases.json
        ("community", "3.27.x", "nightly-3.27.x"),
        ("enterprise", "3.27.x", "3.27.x"),
        ("community", "master", "nightly-master"),
        ("enterprise", "master", "master"),
    ],
)
def test_release_branch(project: str, version: str, branch: str) -> None:
    assert release_branch(project, version) == branch
