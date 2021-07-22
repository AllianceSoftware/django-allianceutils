#!/bin/bash
set -o errexit
set -o nounset
set -o pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# TOX_ENV_RE is set on CI to filter the default environment list
if [[ ${TOX_ENV_RE:-} = "" ]] ; then
	# The empty string is to work around this:
	# https://stackoverflow.com/questions/7577052/bash-empty-array-expansion-with-set-u/61551944
	args=( "$@" "" )

else
	if [[ $# -gt 0 ]] ; then
		echo "TOX_ENV_RE and command line arguments are not compatible" >&2
		exit 1
	fi
	# this will find every tox environment matching TOX_ENV_RE and will run that

	envs=$( tox --listenvs | { egrep "$TOX_ENV_RE" || true ; } | tr '\n' ',' | sed -E 's/,$//' )

	if [[ $envs = "" ]] ; then
		echo "Skipping; TOX_ENV_RE does not match any tox environments"
		exit
	fi

	args=( "$@" -e "$envs" )
fi

set -x
tox "${args[@]}"
