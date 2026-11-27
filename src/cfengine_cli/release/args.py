import argparse
import re


def release_version(value: str) -> str:
    """argparse type for a release or nightly version."""
    if not re.fullmatch(r"\d+\.\d+\.(\d+|x)|master", value):
        raise argparse.ArgumentTypeError(
            f"'{value}' is not X.Y.Z, or X.Y.x or master for nightlies"
        )
    return value


def stable_version(value: str) -> str:
    """argparse type for a release version, not a nightly."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise argparse.ArgumentTypeError(f"'{value}' is not X.Y.Z")
    return value


def add_release_args(sp: argparse.ArgumentParser) -> None:
    _ = sp.add_argument(
        "--project",
        required=True,
        choices=["enterprise", "community"],
        help="Which edition to release",
    )
    _ = sp.add_argument(
        "--version",
        required=True,
        type=release_version,
        help="Version to release, e.g. 3.30.0. Or 3.30.x / master for nightlies",
    )
    _ = sp.add_argument(
        "--build",
        required=True,
        help="Directory with the build",
    )
    _ = sp.add_argument(
        "--output",
        required=True,
        help="Root directory to write release/ and release-data/ to",
    )
    _ = sp.add_argument(
        "--dry-run", action="store_true", help="Only print what would be done"
    )


def add_publish_args(sp: argparse.ArgumentParser) -> None:
    _ = sp.add_argument(
        "--output",
        required=True,
        help="Root directory with release/, repo/ and release-data/",
    )
    _ = sp.add_argument(
        "--bucket",
        required=True,
        choices=["test", "prod"],
        help="test: only the repos, to try them. prod: everything, release data last",
    )
    _ = sp.add_argument(
        "--release-data-only",
        action="store_true",
        help="Only upload the release data, e.g. for nightlies. Needs --bucket prod",
    )
    _ = sp.add_argument(
        "--dry-run", action="store_true", help="Only list what would be uploaded"
    )


def add_update_repo_args(sp: argparse.ArgumentParser) -> None:
    _ = sp.add_argument(
        "--version",
        required=True,
        type=stable_version,
        help="Community version to add, e.g. 3.30.0",
    )
    _ = sp.add_argument(
        "--build",
        required=True,
        help="Directory with the build, as given to cfengine dev release",
    )
    _ = sp.add_argument(
        "--output",
        required=True,
        help="Root directory with release/ and repo/, as given to cfengine dev release",
    )
    _ = sp.add_argument(
        "--dry-run", action="store_true", help="Only print what would be done"
    )
