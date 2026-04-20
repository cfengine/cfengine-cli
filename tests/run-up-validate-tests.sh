#!/usr/bin/env bash

set -e

echo "These tests expect cfengine CLI to be installed globally or in venv"

echo "Looking for CFEngine CLI"
cfengine --version

echo "Check that test files are in expected location:"
ls -al tests/up-validate/*.yaml

rm -rf tmp
mkdir -p tmp/bin
mkdir -p tmp/home/.cfengine/cf-remote

# Mocking vagrant
cp tests/up-validate/mocks/vagrant tmp/bin/.
export PATH="$(pwd)/tmp/bin:$PATH"

# Mocking cloud_config.json
cp tests/up-validate/mocks/cloud_config.json tmp/home/.cfengine/cf-remote/.
MOCK_HOME="$(pwd)/tmp/home"

for file in tests/up-validate/*.yaml; do
  HOME="$MOCK_HOME" cfengine up "$file" --validate
done

echo "All cfengine up --validate tests successful!"

