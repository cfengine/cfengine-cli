import pytest

from cfengine_cli.release.metadata import release_branch


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
