import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from cfengine_cli.release.build import read_build
from cfengine_cli.release.checksums import verify_build
from cfengine_cli.release.plan import PlannedFile, plan_packages
from cfengine_cli.release.utils import (
    SIGNING_KEY,
    check_disk_space,
    check_tools,
    copy_or_skip,
    exit_on_sigterm,
    is_signed,
    output_lock,
    run,
)
from cfengine_cli.utils import UserError

# The community repos, shared by all branches. The legacy release.py, still
# used for LTS releases, writes to the same repos with the same settings.
REPO_DIR = "repo"
APT_POOL = "apt/packages/pool/main/C"
# Labels whose packages go into the repos, as in the legacy release.py
APT_LABELS = ("PACKAGES_x86_64_linux_debian_12", "PACKAGES_arm_64_linux_debian_12")
YUM_LABELS = {
    "PACKAGES_x86_64_linux_redhat_7": "x86_64",
    "PACKAGES_x86_64_linux_redhat_8": "x86_64",
    "PACKAGES_arm_64_linux_redhat_8": "aarch64",
    "PACKAGES_x86_64_linux_redhat_9": "x86_64",
    "PACKAGES_arm_64_linux_redhat_9": "aarch64",
    "PACKAGES_x86_64_linux_redhat_10": "x86_64",
    "PACKAGES_arm_64_linux_redhat_10": "aarch64",
}
REPO_TOOLS = ("apt-ftparchive", "createrepo_c", "gpg", "rpm")

# The settings of apt-ftparchive.conf in infra, with paths from the repo dir.
# i386 is kept, as the pool still has old i386 packages.
APT_FTPARCHIVE_CONF = """\
Dir {{
   ArchiveDir "{apt}/packages";
   CacheDir   "{apt}/cache/";
}};


Default {{
   Packages::Compress ". gzip bzip2";
   Sources::Compress  ". gzip bzip2";
   Contents::Compress ". gzip bzip2";
}};


TreeDefault {{
   BinCacheDB   "packages-$(SECTION)-$(ARCH).db";
   Directory    "pool/$(SECTION)";
   SrcDirectory "pool/$(SECTION)";
   Packages     "$(DIST)/$(SECTION)/binary-$(ARCH)/Packages";
   Sources      "$(DIST)/$(SECTION)/source/Sources";
   Contents     "$(DIST)/Contents-$(ARCH)";
}};


Tree "dists/stable" {{
    Sections "main";
    Architectures "i386 amd64 arm64";
}}
"""

# The settings of apt-ftparchiveRelease.conf in infra
APT_FTPARCHIVE_RELEASE_CONF = """\
APT::FTPArchive::Release::Codename   "community";
APT::FTPArchive::Release::Origin     "CFEngine";
APT::FTPArchive::Release::Components "main";
APT::FTPArchive::Release::Label      "Official packages";
APT::FTPArchive::Release::Architectures "i386 amd64 arm64";
APT::FTPArchive::Release::Suite         "stable";
"""


@dataclass(frozen=True)
class RepoFile:
    """A package to add to a repo."""

    source: Path
    destination: Path


def plan_repo(planned: list[PlannedFile], output_dir: str) -> list[RepoFile]:
    """Plan the packages to add to the community repos."""
    repo = Path(output_dir) / REPO_DIR
    files: list[RepoFile] = []
    for file in planned:
        # Debug releases publish nothing
        if file.destination is None or file.package is None:
            continue
        # The signed copies in the release dir, so a package has the same
        # checksum on the downloads page and in the repos. The legacy
        # release.py adds the unsigned debs instead, which apt accepts too.
        name = file.destination.name
        if file.package in APT_LABELS and name.endswith(".deb"):
            files.append(RepoFile(file.destination, repo / APT_POOL / name))
        elif file.package in YUM_LABELS and name.endswith(".rpm"):
            yum_dir = repo / "yum" / YUM_LABELS[file.package]
            files.append(RepoFile(file.destination, yum_dir / name))
    return files


def _update_apt(apt: Path, output_dir: str) -> None:
    """Regenerate and sign the APT metadata, as update-apt-repo.sh in infra."""
    stable = apt / "packages/dists/stable"
    for directory in (
        apt / "cache",
        apt / "packages/pool/main",
        stable / "main/binary-amd64",
        stable / "main/binary-i386",
        stable / "main/binary-arm64",
        stable / "main/source",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    # In the output dir, so the renames below are atomic
    with tempfile.TemporaryDirectory(dir=output_dir, prefix=".tmp-") as tmp:
        temporary = Path(tmp)
        conf = temporary / "apt-ftparchive.conf"
        _ = conf.write_text(APT_FTPARCHIVE_CONF.format(apt=apt))
        release_conf = temporary / "apt-ftparchiveRelease.conf"
        _ = release_conf.write_text(APT_FTPARCHIVE_RELEASE_CONF)
        _ = run(["apt-ftparchive", "generate", str(conf)])
        release = run(
            ["apt-ftparchive", "-c", str(release_conf), "release", str(stable)]
        )
        release_file = temporary / "Release"
        _ = release_file.write_text(release)

        gpg = ["gpg", "--yes", "--armor", "--digest-algo=SHA256"]
        gpg += ["--local-user", SIGNING_KEY]
        signature = str(temporary / "Release.gpg")
        _ = run([*gpg, "--detach-sign", "--output", signature, str(release_file)])
        # The same signature embedded, the modern way
        in_release = str(temporary / "InRelease")
        _ = run([*gpg, "--clearsign", "--output", in_release, str(release_file)])

        # Signed first, then all moved in at once, so Release never disagrees
        # with its signatures while gpg runs
        for name in ("Release", "Release.gpg", "InRelease"):
            _ = (temporary / name).rename(stable / name)


def _update_yum(directory: Path) -> None:
    """Regenerate and sign the YUM metadata of one arch."""
    _ = run(["createrepo_c", "--simple-md-filenames", str(directory)])
    _ = run(
        [
            "gpg",
            "--yes",
            "--armor",
            "--local-user",
            SIGNING_KEY,
            "--detach-sign",
            str(directory / "repodata/repomd.xml"),
        ]
    )


def update_repo(version: str, build_dir: str, output_dir: str, *, dry_run: bool) -> int:
    """Add a community release to the repos, after cfengine dev release."""
    if not os.path.isdir(build_dir):
        raise UserError(f"Build directory '{build_dir}' does not exist")
    exit_on_sigterm()

    print(f"Updating the community repositories with {version}")
    print(f"  build:  {build_dir}")
    print(f"  output: {output_dir}")
    print(f"  dry run: {dry_run}")

    build = read_build(build_dir)
    verify_build(build)
    planned = plan_packages("community", version, build, output_dir, False)
    files = plan_repo(planned, output_dir)
    _print_repo_plan(files)
    with output_lock(output_dir, dry_run=dry_run):
        update_repos(files, output_dir, dry_run=dry_run)
    return 0


def _print_repo_plan(files: list[RepoFile]) -> None:
    print(f"Planned {len(files)} repository files:")
    for file in files:
        print(f"  {file.destination.name}")
        print(f"    from: {file.source}")
        print(f"    to:   {file.destination}")


def update_repos(files: list[RepoFile], output_dir: str, *, dry_run: bool) -> None:
    """Add the planned packages to the repos, and regenerate their metadata.

    The metadata is regenerated from all packages in the repo, so a failed
    run is repaired by running again.
    """
    if not files:
        return
    missing = [str(file.source) for file in files if not file.source.exists()]
    if missing:
        raise UserError(
            f"Not found, run cfengine dev release first: {', '.join(missing)}"
        )
    check_tools("Repository", REPO_TOOLS)
    # cfengine dev release always signs, so this only fails if the release
    # dir was changed by hand. yum clients with gpgcheck would fail.
    unsigned = [str(file.source) for file in files if not is_signed(file.source)]
    if unsigned:
        raise UserError(f"Not signed, cannot add to the repo: {', '.join(unsigned)}")
    check_disk_space([(f.source, f.destination) for f in files], output_dir)

    for file in files:
        copy_or_skip(
            file.source, file.destination, output_dir, signed=False, dry_run=dry_run
        )

    repo = Path(output_dir) / REPO_DIR
    apt = any(file.destination.name.endswith(".deb") for file in files)
    yum_dirs = sorted(
        {file.destination.parent for file in files if file.destination.suffix == ".rpm"}
    )
    if apt:
        if dry_run:
            print(f"Would have updated the APT repo in '{repo / 'apt'}'")
        else:
            _update_apt(repo / "apt", output_dir)
            print(f"Updated the APT repo in '{repo / 'apt'}'")
    for yum_dir in yum_dirs:
        if dry_run:
            print(f"Would have updated the YUM repo in '{yum_dir}'")
        else:
            _update_yum(yum_dir)
            print(f"Updated the YUM repo in '{yum_dir}'")
