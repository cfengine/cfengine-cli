from pathlib import Path

import pytest

from cfengine_cli.release.publish import plan_syncs, publish
from cfengine_cli.utils import UserError


def test_plan_syncs_prod() -> None:
    urls = [url for _, url, _ in plan_syncs("/output", "prod", False)]
    assert urls == [
        "s3://cfengine-package-repos/enterprise",
        "s3://cfengine-package-repos/community_binaries",
        "s3://cfengine-package-repos/tarballs",
        "s3://cfengine-package-repos/pub",
        # Last, so it never links to files that are not uploaded yet
        "s3://cfengine-package-repos/release-data",
    ]


def test_plan_syncs_test() -> None:
    assert plan_syncs("/output", "test", False) == [
        (Path("/output/repo"), "s3://cfengine-repotest/pub", ["--exclude", "*.old"])
    ]


def test_publish_release_data_only_needs_prod(tmp_path: Path) -> None:
    with pytest.raises(UserError, match="--release-data-only needs --bucket prod"):
        _ = publish(str(tmp_path), "test", release_data_only=True, dry_run=True)


def test_publish_nothing(tmp_path: Path) -> None:
    with pytest.raises(UserError, match="Nothing to publish"):
        _ = publish(str(tmp_path), "prod", release_data_only=False, dry_run=True)


def test_publish_missing_upload_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    (tmp_path / "release-data").mkdir()
    with pytest.raises(UserError, match="Upload tools not found: aws"):
        _ = publish(str(tmp_path), "prod", release_data_only=True, dry_run=True)
