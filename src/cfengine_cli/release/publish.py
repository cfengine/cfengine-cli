import subprocess
from pathlib import Path

from cfengine_cli.release.release_data import RELEASE_DATA_DIR
from cfengine_cli.release.utils import check_tools
from cfengine_cli.utils import UserError

# As in sync-packages-to-s3.sh in infra
BUCKETS = {"test": "cfengine-repotest", "prod": "cfengine-package-repos"}
RELEASE_DIRS = ("enterprise", "community_binaries", "tarballs")
# Backups made by the legacy release.py
REPO_EXCLUDES = ["--exclude", "*.old"]


def plan_syncs(
    output_dir: str, bucket: str, release_data_only: bool
) -> list[tuple[Path, str, list[str]]]:
    """Return the syncs to run, in order: local dir, S3 URL, extra options."""
    output = Path(output_dir)
    s3 = f"s3://{BUCKETS[bucket]}"
    if bucket == "test":
        # Only the repos have a test bucket, to try installing from them
        return [(output / "repo", f"{s3}/pub", REPO_EXCLUDES)]

    syncs: list[tuple[Path, str, list[str]]] = []
    if not release_data_only:
        for name in RELEASE_DIRS:
            syncs.append((output / "release" / name, f"{s3}/{name}", []))
        syncs.append((output / "repo", f"{s3}/pub", REPO_EXCLUDES))
    # Last, so the metadata never links to files that are not uploaded yet
    syncs.append((output / RELEASE_DATA_DIR, f"{s3}/{RELEASE_DATA_DIR}", []))
    return syncs


def publish(
    output_dir: str, bucket: str, *, release_data_only: bool, dry_run: bool
) -> int:
    """Upload the release files, repos and release data to S3."""
    if release_data_only and bucket != "prod":
        raise UserError("--release-data-only needs --bucket prod")

    syncs: list[tuple[Path, str, list[str]]] = []
    for directory, url, options in plan_syncs(output_dir, bucket, release_data_only):
        if directory.is_dir():
            syncs.append((directory, url, options))
        else:
            print(f"Skipped '{directory}', not found")
    if not syncs:
        raise UserError(f"Nothing to publish in '{output_dir}'")
    check_tools("Upload", ("aws",))

    for directory, url, options in syncs:
        command = ["aws", "s3", "sync", str(directory), url, "--acl", "public-read"]
        command += options
        if dry_run:
            # Lists what would be uploaded, the files exist by now
            command.append("--dryrun")
        # Not captured, so the progress of large uploads shows as it runs
        try:
            _ = subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            raise UserError(f"Command failed: {' '.join(command)}") from e
        print(f"{'Checked' if dry_run else 'Uploaded'} '{directory}' to '{url}'")
    return 0
