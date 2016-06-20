#!/bin/bash -e
set -o pipefail

function checkdep() {
	if ! `which $1 >/dev/null` ; then
		echo "Can't find $1; try: " >&2
		echo " $2" >&2
		exit 1
	fi
}

checkdep dot "brew install graphviz"
checkdep sfood "pip install snakefood"

cd `dirname $0`/../..

# user can clean these up manually
CLUSTERFILE=tmp.internaldeps.cluster.txt
PDFFILE=tmp.internaldeps.pdf


find . -type d -depth 1 | sed 's/.\///' > $CLUSTERFILE

sfood . --internal --follow | grep -v allianceutils | sfood-cluster -f $CLUSTERFILE | sfood-graph --pythonify-filenames | dot -Tps | pstopdf -i -o $PDFFILE

open $PDFFILE
