from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.utils import copy_or_skip


def copy_files(planned: list[PlannedFile], output_dir: str, *, dry_run: bool) -> None:
    """Copy the planned files to their destinations.

    Existing destinations are skipped, so a failed run can be resumed. Files
    without a destination (debug releases) are not copied.
    """
    for file in planned:
        if file.destination is None:
            continue
        copy_or_skip(file.source, file.destination, output_dir, dry_run=dry_run)
