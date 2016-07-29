#!/bin/bash
set -o errexit
set -o pipefail

cd $(dirname $0)/..

# Set up mysql details for CI server
if [ "$CI_SERVER" = "yes" ] && ! [ -e ~/.my.cnf ] ; then
    cat  > ~/.my.cnf <<-EOM
		[mysql]
		host="$MYSQL_HOST"
		user="$MYSQL_USER"
		password="$MYSQL_ROOT_PASSWORD"
		default-character-set=utf8mb4

		[client]
		database="$MYSQL_DATABASE"
	EOM
fi

tox
