#!/bin/bash -e
set -o pipefail

cd "$(dirname "$BASH_SOURCE")/.."

bin/reformat-imports.sh --check-only "$@"
