#!/bin/bash

set -e
set -x

uv lock --check
uv build
pip install .
cfengine --version
bash tests/docker/0*.sh
bash tests/shell/0*.sh