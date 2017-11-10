#!/bin/bash -e
set -o pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.inc"

require_virtualenv

if [[ "$1" = "--check-only" ]] ; then
	check_only="--check-only"
	shift
else
    # Insist on an explicit target if we're going to be modifying files
	if [[ $# -eq 0 ]] ; then
        echo "You must specify something to reformat" >&2
        exit 1
	fi
fi

# first try a symlink in this dir
isort_cmd="$(dirname "${BASH_SOURCE[0]}")/isort"

# then the current virtualenv
if ! [ -x "$isort_cmd" ] ; then
	isort_cmd="$VIRTUAL_ENV/bin/isort"
fi

# then whatever the OS has available
if ! [ -x "$isort_cmd" ] ; then
	isort_cmd="$(which isort || true)"
fi

if ! [ -x "$isort_cmd" ] ; then
	echo "Can't find isort; this may not work trying to commit from a GUI" >&2
	echo "You can try symlinking isort in the $(dirname "${BASH_SOURCE[0]}") directory" >&2
	exit 1
fi

"$isort_cmd" \
    --settings-path "$project_dir" \
	--recursive \
	$check_only \
	"${@:-$base_dir}"
