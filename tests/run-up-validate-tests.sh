#!/usr/bin/env bash

function assert_contains()
{
  local haystack="$1"
  local needle="$2"
  if [[ ! "$haystack" =~ $needle ]]; then
      exit 1
  fi
}

set -e

echo "These tests expect cfengine CLI to be installed globally or in venv"

echo "Looking for CFEngine CLI"
cfengine --version

echo "Check that test files are in expected location:"
ls -al tests/up-validate/*.yaml

rm -rf tmp
mkdir -p tmp/bin
mkdir -p tmp/home/.config/cfengine/cf-remote
mkdir -p tmp/home/.cache/cfengine/cf-remote

# Mocking vagrant
cp tests/up-validate/mocks/vagrant tmp/bin/.
CURRENT_PWD=$(pwd)
export PATH="$CURRENT_PWD/tmp/bin:$PATH"

# Mocking cloud_config.json
cp tests/up-validate/mocks/cloud_config.json tmp/home/.config/cfengine/cf-remote/.
MOCK_HOME="$CURRENT_PWD/tmp/home"

shopt -s extglob

for file in tests/up-validate/!(*.x).yaml; do
  HOME="$MOCK_HOME" cfengine up "$file" --validate
done

for file in tests/up-validate/*.x.yaml; do
  ret="$(HOME="$MOCK_HOME" cfengine up "$file" --validate || true)"
  assert_contains "$ret" "Error"
done  


echo "All cfengine up --validate tests successful!"
