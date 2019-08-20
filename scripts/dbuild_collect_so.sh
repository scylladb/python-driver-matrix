#!/usr/bin/env bash
set -e

HELP="
Tool collect all the .so a scylla binary is depended on
so it can later be used be ccm/dtest

    ./dbuild_collect_so.sh [scylla binary] [output directory]
"

if (( $# != 2 )); then
    echo "${HELP}"
    exit 1
fi
SCYLLA_BIN=$1
OUTPUT_DIR=$2
[[ -f "${SCYLLA_BIN}" ]] || (echo "${SCYLLA_BIN} doesn't exists" ; echo "${HELP}" ; exit 1 )
if [[ ! -d "${OUTPUT_DIR}" ]]; then
  echo "creating output dir [${OUTPUT_DIR}]"
  mkdir ${OUTPUT_DIR}
fi
ldd ${SCYLLA_BIN} | sed 's/^.*\s\(.*\)\s(.*)/\1/' | xargs -i cp {} ${OUTPUT_DIR}
