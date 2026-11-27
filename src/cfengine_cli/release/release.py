import datetime
import os

from cfengine_cli.release.build import read_build
from cfengine_cli.release.checksums import verify_build
from cfengine_cli.release.metadata import is_nightly, release_branch
from cfengine_cli.release.plan import PlannedFile, plan_assets, plan_packages
from cfengine_cli.release.copy_files import copy_files
from cfengine_cli.release.release_data import write_release_data
from cfengine_cli.release.utils import (
    check_disk_space,
    exit_on_sigterm,
    output_lock,
)
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

    exit_on_sigterm()

    _print_summary(
        project,
        version,
        branch,
        build_dir,
        output_dir,
        debug,
        dry_run,
    )

    build = read_build(build_dir)
    verify_build(build)

    planned = plan_packages(project, version, build, output_dir, debug) + plan_assets(
        project, version, build, output_dir, debug
    )
    _print_plan(planned)

    with output_lock(output_dir, dry_run=dry_run):
        check_disk_space([(f.source, f.destination) for f in planned], output_dir)
        copy_files(planned, output_dir, dry_run=dry_run)
        write_release_data(
            project,
            version,
            branch,
            debug,
            planned,
            output_dir,
            dry_run=dry_run,
            today=datetime.date.today(),
        )
    return 0


def _print_plan(planned: list[PlannedFile]) -> None:
    print(f"Planned {len(planned)} files:")
    section = None
    for file in planned:
        if file.section != section:
            section = file.section
            print(f"  {section}")
        print(f"    {file.source.name}")
        print(f"      from: {file.source}")
        print(f"      to:   {file.destination or 'not copied'}")
        print(f"      url:  {file.url}")


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
