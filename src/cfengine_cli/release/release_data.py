import datetime
import json
import urllib.request
from http.client import HTTPResponse
from pathlib import Path
from typing import cast

from cfengine_cli.release.checksums import file_sha256
from cfengine_cli.release.metadata import (
    Artifact,
    ReleasesData,
    VersionDocument,
    release_data_url,
    update_releases,
    version_document,
)
from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.utils import atomic_write
from cfengine_cli.utils import UserError

# Uploaded to release-data on S3 by cfengine dev publish
RELEASE_DATA_DIR = "release-data"


def build_artifacts(
    planned: list[PlannedFile], dry_run: bool
) -> tuple[dict[str, list[Artifact]], list[str]]:
    """Return the artifacts and footnotes of release-data/<project>/<version>.json.

    Artifacts are grouped by section, in the order of the plan.
    """
    artifacts: dict[str, list[Artifact]] = {}
    footnotes: list[str] = []
    for file in planned:
        artifact: Artifact = {
            "Title": file.title,
            "Arch": file.arch,
            "classexpr": file.classexpr,
            "Published": True,
            "URL": file.url,
            "SHA256": file_sha256(_downloaded_file(file, dry_run)),
        }
        if file.footnote is not None:
            # Numbered from 1, in order of first use
            if file.footnote not in footnotes:
                footnotes.append(file.footnote)
            artifact["Footnote"] = footnotes.index(file.footnote) + 1
        if file.instructions is not None:
            artifact["Instructions"] = file.instructions
        if file.package is not None:
            artifact["package"] = file.package
        artifacts.setdefault(file.section, []).append(artifact)
    return artifacts, footnotes


def _downloaded_file(file: PlannedFile, dry_run: bool) -> Path:
    """Return the file users download, i.e. the signed copy if any.

    A dry run copies nothing, so it falls back to the source, as the legacy
    release.py does. Debug releases link to the source.
    """
    if dry_run or file.destination is None:
        return file.source
    return file.destination


def _read_releases(path: Path, project: str) -> ReleasesData:
    """Read releases.json, or fetch the published one if there is none yet."""
    if path.exists():
        try:
            return cast(ReleasesData, json.loads(path.read_text()))
        except json.JSONDecodeError as e:
            raise UserError(f"Invalid JSON in '{path}': {e}") from e
    url = release_data_url(project, "releases")
    print(f"No '{path}', fetching '{url}'")
    try:
        # urlopen() is typed Any, but returns this for http(s) URLs
        response = cast(HTTPResponse, urllib.request.urlopen(url, timeout=60))
        with response:
            return cast(ReleasesData, json.load(response))
    except OSError as e:
        # Unlike the legacy release.py, do not start from an empty list. It
        # would replace the published releases.json once uploaded.
        raise UserError(f"Could not fetch '{url}': {e}") from e
    except json.JSONDecodeError as e:
        raise UserError(f"Invalid JSON from '{url}': {e}") from e


def _write_json(
    path: Path,
    data: ReleasesData | VersionDocument,
    output_dir: str,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        print(f"Would have written '{path}'")
        return
    with atomic_write(path, output_dir) as temporary:
        # Same format as the legacy release.py
        _ = temporary.write_text(json.dumps(data, indent=4))
    print(f"Wrote '{path}'")


def write_release_data(
    project: str,
    version: str,
    branch: str,
    debug: bool,
    planned: list[PlannedFile],
    output_dir: str,
    *,
    dry_run: bool,
    today: datetime.date,
) -> None:
    """Write release-data/<project>/<version>.json and update releases.json."""
    directory = Path(output_dir) / RELEASE_DATA_DIR / project
    releases_path = directory / "releases.json"

    artifacts, footnotes = build_artifacts(planned, dry_run)
    document = version_document(project, version, branch, artifacts, footnotes, today)
    releases = update_releases(
        _read_releases(releases_path, project), project, version, branch, debug, today
    )

    # The document first, so releases.json never links to a missing one
    _write_json(directory / f"{version}.json", document, output_dir, dry_run=dry_run)
    _write_json(releases_path, releases, output_dir, dry_run=dry_run)
