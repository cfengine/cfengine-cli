import os

from cfengine_cli.release.metadata import is_nightly, release_branch
from cfengine_cli.utils import UserError


def release(
    project: str,
    version: str,
    build_dir: str,
    output_dir: str,
    dry_run: bool,
) -> int:
    branch = release_branch(project, version)
    # Nightlies are debug releases causing them to be hidden from the downloads page
    debug = is_nightly(version)
    if not os.path.isdir(build_dir):
        raise UserError(f"Build directory '{build_dir}' does not exist")

    _print_summary(
        project,
        version,
        branch,
        build_dir,
        output_dir,
        debug,
        dry_run,
    )
    return 0


def _print_summary(
    project: str,
    version: str,
    branch: str,
    build_dir: str,
    output_dir: str,
    debug: bool,
    dry_run: bool,
) -> None:
    print(f"Releasing {project} {version} (branch {branch})")
    print(f"  build:  {build_dir}")
    print(f"  output: {output_dir}")
    print(f"  debug:  {debug}")
    print(f"  dry run: {dry_run}")
