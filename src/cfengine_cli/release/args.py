import argparse
import re


def release_version(value: str) -> str:
    """argparse type for a release or nightly version."""
    if not re.fullmatch(r"\d+\.\d+\.(\d+|x)|master", value):
        raise argparse.ArgumentTypeError(
            f"'{value}' is not X.Y.Z, or X.Y.x or master for nightlies"
        )
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
