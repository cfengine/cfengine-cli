#!/bin/bash

set -e
set -x

uv lock --check
uv run flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
uv run flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
uv run pytest