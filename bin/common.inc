# exports the following items:
#
# functions:
#  realpath() - resolve a path containing symlinks or .. to the real path
#
# general variables:
#  REPO_DIR - root of the git repository
#  SOURCE_ROOT - root of the python source


function realpath() {
    # OSX readlink does not contain the canonicalize functionality that gnu readlink does
    # so we do this in python
    python -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$1"
}

# BASE_DIR and PROJECT_DIR should resolve to the same thing as in the django settings file
REPO_DIR="$(realpath "$(dirname "${BASH_SOURCE[0]}")/..")"

SOURCE_ROOT="$REPO_DIR/allianceutils"
