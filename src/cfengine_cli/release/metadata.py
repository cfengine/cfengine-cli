import re


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
