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
FILE_PREFIX="report"
RET_VALS=0

function sig_handler(){
    echo -e "Signal caught. Exiting from tests..."
    exit 1
}

trap sig_handler INT TERM

while getopts ":o:" flag; do
	case "${flag}" in
        o)
            if [[ "${OPTARG}" = /* ]]; then
                REPORT_PATH="${OPTARG}"
            else
                REPORT_PATH=$(realpath "${SUITES_DIR}/${OPTARG}")
            fi
            echo -e "\n[x] JUnit-style reports are configured with path: ${REPORT_PATH}\n"
            echo -e "Preparing report folder..."
            [[ -d "${REPORT_PATH}" ]] && rm -rfv "${REPORT_PATH}"
            mkdir -pv "${REPORT_PATH}"
            ;;
        :)
            echo "Missing value for parameter: -${OPTARG} !"
            exit 1;;
        ?)
            echo "Invalid parameter: -${OPTARG} !"
            exit 1;;
    esac
done

for testfile in "${SUITES_DIR}"/test-*.sh; do
    [ -e "${testfile}" ] || continue
    echo -e "\nExecuting ${testfile}...\n"
    if [ -v REPORT_PATH ]; then
        REPORT_FILE=$(basename -- "${testfile}" ".sh")
        ( exec bash "${testfile}" -- --output-junit-xml="${REPORT_PATH}/${FILE_PREFIX}-${REPORT_FILE}.xml" 2>&1; )
        RET_VALS=$(( "${RET_VALS}" + "$?" ))
    else
        ( exec bash "${testfile}" 2>&1; )
        RET_VALS=$(( "${RET_VALS}" + "$?" ))
    fi
done

[[ ${RET_VALS} -eq 0 ]] && exit 0 || exit 1
