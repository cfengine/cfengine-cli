#!/bin/bash

set -e
set -x

# Setup: create a temp directory for test files
tmpdir=$(mktemp -d)
output_file=$(mktemp)
trap "rm -rf $tmpdir $output_file" EXIT

# Empty JSON file
printf "" > "$tmpdir/empty.json"

# Empty CSV file
printf "" > "$tmpdir/empty.csv"

# Empty policy file
printf "" > "$tmpdir/empty.cf"

# CSV with LF-only line endings
printf 'a,b,c\n1,2,3\n' > "$tmpdir/bad.csv"

# JSON with just some characters
printf 'abc\n' > "$tmpdir/bad.json"

# Policy file with just some characters
printf 'abc\n' > "$tmpdir/bad.cf"

# Run lint on the folder - expect non-zero exit
if cfengine lint "$tmpdir" > "$output_file" 2>&1; then
	cat "$output_file"
	echo "FAIL: expected lint to fail, but it succeeded"
	exit 1
fi
cat "$output_file"

# Verify each file is reported as failing
grep -q "FAIL:.*empty.json" "$output_file"
grep -q "FAIL:.*empty.csv" "$output_file"
grep -q "FAIL:.*empty.cf" "$output_file"
grep -q "FAIL:.*bad.csv" "$output_file"
grep -q "FAIL:.*bad.json" "$output_file"
grep -q "FAIL:.*bad.cf" "$output_file"

# Verify total error count is 6
grep -q "Failure, 6 errors in total" "$output_file"
