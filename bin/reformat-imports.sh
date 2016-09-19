#!/bin/bash -e
set -o pipefail

source "$(dirname "$BASH_SOURCE")/common.inc"

if [[ "$1" = "--check-only" ]] ; then
	CHECK_ONLY="--check-only"
	shift
else
    # Insist on an explicit target if we're going to be modifying files
	if [[ $# -eq 0 ]] ; then
        echo "You must specify something to reformat" >&2
        exit 1
	fi
fi

# first try symlink in this dir
ISORT="$(dirname "$BASH_SOURCE")/isort"

# then the current virtualenv
if ! [ -x "$ISORT" ] ; then
	ISORT="$VIRTUAL_ENV/bin/isort"
fi

# then whatever the OS has available
if ! [ -x "$ISORT" ] ; then
	ISORT="$(which isort || true)"
fi

if ! [ -x $ISORT ] ; then
	echo "Can't find isort; this may not work trying to commit from a GUI" >&2
	echo "You can try symlinking isort in the $(dirname "$BASH_SOURCE") directory" >&2
	exit 1
fi

"$ISORT" \
	--settings-path "$SOURCE_ROOT" \
	--recursive \
	--project allianceutils \
	$CHECK_ONLY \
	"${@:-$SOURCE_ROOT}"
