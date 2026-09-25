#!/bin/bash

set -e
set -x

# Setup: a cfbs project (without git) and a custom index in a temp directory
tmpdir=$(mktemp -d)
trap "rm -rf $tmpdir" EXIT
cd "$tmpdir"

cat > cfbs.json <<EOF
{
  "name": "Example project",
  "description": "Example description",
  "type": "policy-set",
  "git": false,
  "build": []
}
EOF

cat > custom.json <<EOF
{
  "name": "custom",
  "type": "index",
  "index": {
    "my-module": {
      "description": "Module only found in the custom index",
      "tags": ["experimental"],
      "repo": "https://github.com/cfengine/modules",
      "by": "https://github.com/cfengine",
      "version": "1.0.0",
      "commit": "e603b586e4028364ceea234f3b71c6e5d78b811e",
      "subdirectory": "management/autorun",
      "steps": ["json def.json def.json"]
    }
  }
}
EOF

# --index is available for commands which look up modules in an index
cfengine add -h | grep -- "--index"
cfengine search -h | grep -- "--index"
cfengine moduleinfo -h | grep -- "--index"

# ...but not for commands which only operate on the project
for command in update remove input; do
	if cfengine $command my-module --index ./custom.json; then
		echo "FAIL: expected '--index' to be rejected by 'cfengine $command'"
		exit 1
	fi
done

# Search and moduleinfo find the module in the custom index
cfengine search my-module --index ./custom.json | grep "my-module - Module only found in the custom index"
cfengine moduleinfo my-module --index ./custom.json | grep "Module only found in the custom index"

# An invalid index string gives an error, not a backtrace
output=$(cfengine search my-module --index custom.json 2>&1) && exit 1
echo "$output" | grep 'must be a URL (starting with https://) or relative path (starting with ./)'
if echo "$output" | grep "Traceback"; then
	exit 1
fi

# Adding from the custom index records the index on the module,
# but does not change the index of the project
cfengine add my-module --index ./custom.json
grep '"name": "my-module"' cfbs.json
grep '"index": "./custom.json"' cfbs.json
grep '"added_by": "cfengine add"' cfbs.json
[ "$(grep -c '"index"' cfbs.json)" = "1" ]

# Remove works without an index (newline accepts the default "yes" in the prompt)
echo | cfengine remove my-module
if grep "my-module" cfbs.json; then
	echo "FAIL: expected my-module to be removed from cfbs.json"
	exit 1
fi
