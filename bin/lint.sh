#!/bin/bash -e
set -o pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

bin/reformat-imports.sh --check-only "$@"
