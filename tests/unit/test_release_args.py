import argparse

import pytest

from cfengine_cli.release.args import release_version


@pytest.mark.parametrize("version", ["3.30.0", "3.27.x", "master"])
def test_release_version(version: str) -> None:
    assert release_version(version) == version


@pytest.mark.parametrize("version", ["3.30", "3.15.0b1", "ENT-1234", "3.27.x.1"])
def test_release_version_invalid(version: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _ = release_version(version)
