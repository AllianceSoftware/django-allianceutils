#!/bin/bash -e
set -o pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.inc"

cd "$repo_dir"

return_code=0

[[ $(pwd) =~ template-django$ ]] && is_template_repo=true || is_template_repo=false

function err() {
	echo "ERROR: $1" >&2
	return_code=1
}
function warn() {
	echo "WARNING: $1" >&2
}

function notice() {
	echo "-----------------------"
	echo $1
}

notice "Linting"

function lint_virtualenv() {
	notice "Linting python virtualenv"
	local virtualenvs_dir
	# virtualenv
	if [[ ! -e .venv ]] ; then
		err "You have no .venv file"
	else
		# are we using the right virtualenv?
		require_virtualenv
		if [[ ${VIRTUAL_ENV##*/} != "$(<.venv)" ]] && ! $is_ci ; then
			warn "Active virtualenv (${VIRTUAL_ENV##*/}) != expected ($(<.venv)). Are you using the right virtualenv?"
		fi
	fi
}

function lint_python_source() {
	if ! $files_all && [[ ${#files_py[@]} -le 0 ]] ; then
	    return 0
    fi

	notice "Linting python source"
    bin/reformat-imports.sh --check-only "${files_py[@]}" | { egrep -v '^Skipped ' || true ; }
}

function lint_secrets() {
	notice "Linting secrets"
	if git ls-files | grep SECRET_KEY >/dev/null ; then
		err "SECRET_KEY should not be committed"
	fi
}

files_py=()
function parse_filelists() {
	local f
	if [[ $# -eq 0 ]] ; then
		files_all=true
	else
		files_all=false
		for f in "$@" ; do
			if [[ $f =~ \.py$ ]] ; then
				files_py+=("$f")
			fi
		done
	fi
}

parse_filelists "$@"

lint_virtualenv
lint_python_source
lint_secrets


exit $return_code
