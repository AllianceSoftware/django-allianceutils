#!/bin/bash
set -o errexit
set -o pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

tox "$@"
