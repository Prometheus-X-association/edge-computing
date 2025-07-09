#!/usr/bin/env bash
# Copyright 2025 Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -ou pipefail

SUITES_DIR=$(readlink -f "$(dirname "$0")")
ROOT_DIR=$(readlink -f "${SUITES_DIR}/../..")
FILE_PREFIX="test-report"
RET_VALS=0

source "${ROOT_DIR}"/test/scripts/helper.sh

function sig_handler(){
    echo "Signal caught. Exiting from tests..."
    exit 1
}

trap sig_handler INT TERM

function display_help() {
    cat <<EOF
Usage: $0 [options]

Options:
    -o <dir>    Generate Junit-style reports into <dir>.
    -h          Display help.
EOF
}

while getopts ":o:h" flag; do
	case "${flag}" in
        o)
            if [[ "${OPTARG}" = /* ]]; then
                REPORT_PATH="${OPTARG}"
            else
                REPORT_PATH=$(realpath "${SUITES_DIR}/${OPTARG}")
            fi
            echo "[x] JUnit-style reports are configured with path: ${REPORT_PATH}"
            echo -e "\nPreparing report folder..."
            [[ -d "${REPORT_PATH}" ]] && rm -rfv "${REPORT_PATH}"
            mkdir -pv "${REPORT_PATH}"
            ;;
        h)
            display_help
            exit
            ;;
        :)
            echo "Missing value for parameter: -${OPTARG} !"
            exit 1;;
        ?)
            echo "Invalid parameter: -${OPTARG} !"
            display_help
            exit 1;;
    esac
done

for testfile in "${SUITES_DIR}"/test-*.sh; do
    [ -e "${testfile}" ] || continue
    log "Executing ${testfile}..."
    if [ -v REPORT_PATH ]; then
        TEST_CASE=$(basename -- "${testfile}" ".sh" | sed -e "s/^test-//")
        REPORT_XML="${REPORT_PATH}/${FILE_PREFIX}-${TEST_CASE}.xml"
        ( exec bash "${testfile}" -- --output-junit-xml="${REPORT_XML}" --suite-name="${TEST_CASE}" 2>&1; )
        RET_VALS=$(( "${RET_VALS}" + "$?" ))
    else
        ( exec bash "${testfile}" 2>&1; )
        RET_VALS=$(( "${RET_VALS}" + "$?" ))
    fi
done

[[ ${RET_VALS} -eq 0 ]] && exit 0 || exit 1
