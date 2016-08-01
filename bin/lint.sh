#!/bin/bash -e
set -o pipefail

cd $(dirname $0)/..

bin/reformatimports.sh --check-only "$@"
