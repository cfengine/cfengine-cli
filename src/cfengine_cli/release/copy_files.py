from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.utils import SIGNED_SUFFIXES, check_tools, copy_or_skip

SIGNING_TOOLS = ("rpm", "rpmsign", "debsigs")


def _to_copy(planned: list[PlannedFile]) -> list[PlannedFile]:
    """Return the files with a destination that does not exist yet."""
    return [
        file
        for file in planned
        if file.destination is not None and not file.destination.exists()
    ]


def copy_files(planned: list[PlannedFile], output_dir: str, *, dry_run: bool) -> None:
    """Copy the planned files to their destinations, signing .rpm and .deb.

    Existing destinations are skipped, so a failed run can be resumed. Files
    without a destination (debug releases) are not copied.
    """
    to_sign = [
        file for file in _to_copy(planned) if file.source.name.endswith(SIGNED_SUFFIXES)
    ]
    if to_sign:
        check_tools("Signing", SIGNING_TOOLS)

    for file in planned:
        if file.destination is None:
            continue
        signed = file.source.name.endswith(SIGNED_SUFFIXES)
        copy_or_skip(
            file.source, file.destination, output_dir, signed=signed, dry_run=dry_run
        )
