#!/bin/bash -e
set -o pipefail

# if on OSX then prefer the gnu version (the osx version does nothing) greadlink
READLINK=`which greadlink || which readlink`

SOURCE_ROOT=`dirname "$($READLINK "$0" || echo $0)"`/..

if [[ "$1" = "--check-only" ]] ; then
	CHECK_ONLY="--check-only"
	shift
fi

ISORT=`which isort || true`

if ! [ -x "$ISORT" ] ; then
	ISORT="$VIRTUAL_ENV/bin/isort"
fi

if ! [ -x "$ISORT" ] ; then
	ISORT="`dirname $0`/isort"
fi

if ! [ -x $ISORT ] ; then
	echo "Can't find isort; this may not work trying to commit from a GUI" >&2
	echo "You can try symlinking isort in the `dirname $0` directory" >&2
	exit 1
fi

$ISORT \
	--settings-path "$SOURCE_ROOT" \
	--recursive \
	--project allianceutils \
	$CHECK_ONLY \
	"${@:-$SOURCE_ROOT}"
