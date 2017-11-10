#@IgnoreInspection BashAddShebang
#
# exports the following items:
#
# functions:
#  realpath() - resolve a path containing symlinks or .. to the real path
#  fail() - print arguments to stderr and exit with a failure code
#
# general variables:
#  MD5SUM - path to the gnu md5sum
#  repo_dir - root of the git repository
#
# django variables: (should match settings.py)
#  is_ci - true or false depending on whether running on a CI server
#  project_dir - root django project path
#  base_dir - django site app path
#  static_dir - collected static files path

realpath=$( command -v realpath >/dev/null 2>&1 ) || function realpath() {
    # OSX readlink does not contain the canonicalize functionality that gnu readlink does
    # so we do this in python
    python -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$1"
}

function require_virtualenv() {
	local virtualenvs_dir

	# validate that a virtualenv is active and if not, try to activate it
	if [ "$VIRTUAL_ENV" = "" ] ; then
		virtualenvs_dir=${WORKON_HOME:-${VIRTUALENVWRAPPER_HOOK_DIR:-~/.virtualenvs}}
		if [[ $( type -t workon ) = "function" ]] ; then
			workon "$(<.venv)"
		elif [[ -e "$virtualenvs_dir/$(<.venv)/bin/activate" ]] ; then
			source "$virtualenvs_dir/$(<.venv)/bin/activate"
		else
			fail "No virtualenv is active (and couldn't find the right one)"
		fi

	fi
}

function fail() {
	echo "$@" >&2
	exit 1
}

function pathadd() {
	if [[ -d "$1" && ":$PATH:" != *":$1:"* ]]; then
		PATH="${PATH:+"$PATH:"}$1"
	fi
}

# If running inside a git GUI, /usr/local/bin may not be on PATH; we need it
if [[ "$OSTYPE" =~ ^darwin ]] ; then
	pathadd /usr/local/bin
fi

MD5SUM="$( which md5sum || which gmd5sum || fail 'Cannot find md5sum' )"
FIND="$( which gfind || which find || fail 'Cannot find GNU findutils' )"

if [[ "$OSTYPE" =~ ^darwin ]] ; then
    # -quit is a GNU findutils extension
	$FIND -quit 2>/dev/null || fail "Missing GNU find; run 'brew install findutils'"
fi

# BASE_DIR and PROJECT_DIR should resolve to the same thing as in the django settings file
repo_dir="$(realpath "$(dirname "${BASH_SOURCE[0]}")/..")"

is_ci="${CI-false}"
project_dir="$repo_dir/"
base_dir="$project_dir/test_allianceutils"
static_dir="$repo_dir/test_allianceutils/static"

cd "$repo_dir"
