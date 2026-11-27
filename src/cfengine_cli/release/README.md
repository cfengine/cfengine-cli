# Releasing CFEngine

These commands release the packages built by `build-in-container`.
They replace the legacy `release.py` and `sync-packages-to-s3.sh` in the infra repo.
Older branches, like `3.24.x` and `3.27.x`, keep using the legacy scripts until they reach EOL.
Both scripts can coexist

## The commands

### `cfengine dev release`

Releases a build. Works on local files only.

1. Reads the build and verifies its `sha256sums.txt` files.
2. Plans every file to publish.
3. Copies the files to `release/`, and signs the packages.
4. Creates the release data: `release-data/<project>/<version>.json`.
   Appends the new version to `release-data/<project>/releases.json`.

Signing is reproducible. The signature time is the build time of the package.

### `cfengine dev update-repo`

Adds a community release to the local copy of the APT and YUM repositories in `repo/` on buildcache.
It regenerates and signs the repository metadata.
It adds the copies in `release/`, signed by `cfengine dev release`, and refuses unsigned ones.

### `cfengine dev publish`

Uploads to S3:

- `--bucket test` uploads the repositories to `cfengine-repotest`.
- `--bucket prod` uploads the release files, the repositories, and the release data to `cfengine-package-repos`.
- `--release-data-only` uploads only the release data, for nightlies.
  Their release data links to the packages on buildcache itself, not on S3.

`--bucket test` uploads less than `--bucket prod`, as only the repositories have a test bucket.
ENT-14959 will fix this asymmetry where everything will go to a staging bucket first.

## Directories

The output directory, `/var/www/buildcache` on buildcache, contains:

- `release/`: the released files, as they are published on S3
- `repo/`: the community APT and YUM repositories
- `release-data/`: the release data, read by the downloads page and cf-remote
- `.lock`: held while writing
- `.tmp-*`: temporary files while writing

The build directory is a `build-in-container output`.
E.g. `/var/www/buildcache/packages/build-in-container/<build>`.

## Requirements

- The `contact@northern.tech` gpg key, to sign the packages and repositories.
- `gpg`, `rpm`, `rpmsign`, `debsigs`, `apt-ftparchive`, `createrepo_c` and `aws`.
- AWS credentials for both buckets.

## Making a release

Community and enterprise are always released together.
Every command takes `--dry-run`, to see what it would do first.
It's safe to run a failed command again.

### Feature release

A feature release is one new version, e.g. `3.31.0`.

1. Set the variables:

   ```bash
   VERSION=3.31.0  # Change to the version you are releasing
   BUILD=/var/www/buildcache/packages/build-in-container/<build>  # Change to its build
   OUTPUT=/var/www/buildcache
   ```

2. Release both projects, and add the community release to the repositories:

   ```bash
   cfengine dev release --project community --version $VERSION --build $BUILD --output $OUTPUT
   cfengine dev release --project enterprise --version $VERSION --build $BUILD --output $OUTPUT
   cfengine dev update-repo --version $VERSION --build $BUILD --output $OUTPUT
   ```

3. Upload the repositories to the test bucket, and check that installing from
   them works:

   ```bash
   cfengine dev publish --output $OUTPUT --bucket test
   ```

4. When the release is announced, upload everything to production:

   ```bash
   cfengine dev publish --output $OUTPUT --bucket prod
   ```

### Patch release

A patch release is made on each supported LTS branch at the same time.
E.g. `3.33.1` and `3.30.4`. Each version has its own build.

1. Set the variables:

   ```bash
   A_VERSION=3.33.1  # Change to the version on one LTS branch
   A_BUILD=/var/www/buildcache/packages/build-in-container/<build>  # Change to its build
   B_VERSION=3.30.4  # Change to the version on the other LTS branch
   B_BUILD=/var/www/buildcache/packages/build-in-container/<build>  # Change to its build
   OUTPUT=/var/www/buildcache
   ```

2. Release both projects of both versions, and add the community releases to the repositories:

   ```bash
   cfengine dev release --project community --version $A_VERSION --build $A_BUILD --output $OUTPUT
   cfengine dev release --project enterprise --version $A_VERSION --build $A_BUILD --output $OUTPUT
   cfengine dev update-repo --version $A_VERSION --build $A_BUILD --output $OUTPUT
   cfengine dev release --project community --version $B_VERSION --build $B_BUILD --output $OUTPUT
   cfengine dev release --project enterprise --version $B_VERSION --build $B_BUILD --output $OUTPUT
   cfengine dev update-repo --version $B_VERSION --build $B_BUILD --output $OUTPUT
   ```

3. Upload the repositories to the test bucket, and check that installing from them works.
   This uploads both versions at once:

   ```bash
   cfengine dev publish --output $OUTPUT --bucket test
   ```

4. When the release is announced, upload everything to production:

   ```bash
   cfengine dev publish --output $OUTPUT --bucket prod
   ```

Use legacy script in infra for versions older that `3.30`.

## Nightlies

When a nightly build finishes, Jenkins puts its output in `/home/jenkins/output/`.
The `sync.path` systemd unit on buildcache notices it and starts `sync.service`, which runs `sync.sh` from the infra repo.
It copies the build to `/var/www/buildcache/packages/`, and releases it with the branch as the version, e.g. `master` or `3.30.x`.

For a community master nightly:

```bash
cfengine dev release --project community --version master --build $BUILD --output /var/www/buildcache
cfengine dev publish --output /var/www/buildcache --bucket prod --release-data-only
```

A nightly copies and signs nothing.
Its release data links to the build on buildcache, so only the release data is uploaded.

## Code

The commands are added in `main.py` and dispatched in `dev.py`.
Each starts in the function of the same name, in the file of the same name:

- `release`: `release()` in `release.py`
- `update-repo`: `update_repo()` in `update_repo.py`
- `publish`: `publish()` in `publish.py`

The files in this directory:

- `args.py`: the command line options.
- `build.py`: reads the `build-in-container` output directory into a `Build`, one `PackageDir` per platform label.
- `checksums.py`: verifies the build against its `sha256sums.txt` files, and hashes files.
- `platforms.py`: what a build label means.
  E.g. that `PACKAGES_arm_64_linux_ubuntu_24` is "Ubuntu 24", aarch64, with its classexpr and release directory.
  Also decides the order of packages on the downloads page.
- `plan.py`: plans every file to publish as a `PlannedFile`:
  where it comes from, where it goes, its URL, and how it is shown in the release data.
  Most release rules live here.
- `release.py`: the `release` command. Reads, plans, copies and writes the release data.
- `copy_files.py`: copies the planned files to `release/`, and signs packages.
- `metadata.py`: the release data formats, and the logic around versions:
  titles, LTS branches, support dates, and the `latest` flags in `releases.json`.
- `release_data.py`: builds the release data from the plan, and reads and writes the JSON files.
- `update_repo.py`: the `update-repo` command.
  Adds packages to the APT and YUM repositories, and regenerates and signs the repository metadata.
- `publish.py`: the `publish` command. Uploads the directories to S3 in a safe order.
- `utils.py`: shared helpers.

The unit tests live in `tests/unit/test_release_<module>.py`.
End-to-end tests live in `tests/release/`.
