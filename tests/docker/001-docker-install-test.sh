#!/bin/bash

# This test sets up a docker container running an SSH server,
# where we test ssh based commands
# (such as cf-remote install).
# TODO: Actually install / test something in container

set -ex
set -o pipefail

rm -f log
error () {
  echo "=== error occurred, rc=$?, logs follow ==="
  [ -f log ] && cat log
}
trap error ERR

dir=$(dirname "$0")
name=cfengine-cli-debian-test-host

docker stop "$name" || true
docker rm "$name" || true
docker build -t "$name" "$dir" >log 2>&1
docker run -d -p 8822:22 --name "$name" "$name" >>log 2>&1
ip_addr=$(hostname -i)
ssh -o StrictHostKeyChecking=no -p 8822 root@"$ip_addr" hostname >>log 2>&1
echo "ssh returned exit code $?"
echo "=== cf-remote --version ===" | tee -a log
cf-remote --version 2>&1 | tee -a log
echo "cf-remote --version got return code $?"
echo "=== cfengine version ===" | tee -a log
cfengine version 2>&1 | tee -a log
echo "=== cfengine --version ===" | tee -a log
cfengine --version 2>&1 | tee -a log
echo "=== cfengine help ===" | tee -a log
cfengine help 2>&1 | tee -a log
