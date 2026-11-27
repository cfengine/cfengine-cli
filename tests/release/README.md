# Release end-to-end test

`e2e.sh` tests `cfengine dev release` and `cfengine dev update-repo` with the
real packaging and signing tools. It recreates published community and
enterprise releases from small fake packages, and compares the release data
with the published one. It also checks a master nightly. CI runs it
as its own job, see `.github/workflows/make-check.yml`.

```bash
uv run bash tests/release/e2e.sh
```

It needs gpg, rpm, rpmbuild, rpmsign, debsigs, apt-ftparchive and
createrepo_c. It uses its own gpg key, never a real keyring.

## Data

The files in `data/` are release data from
`https://cfengine-package-repos.s3.amazonaws.com/release-data/`, named
`<project>-<version>.json` and `<project>-releases.json`. They are excluded
from prettier, to keep the published format.
