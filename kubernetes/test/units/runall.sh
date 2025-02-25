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

set -eou pipefail

SUITES_DIR=$(readlink -f "$(dirname "$0")")
ROOT_DIR=$(readlink -f "${SUITES_DIR}/../..")
RET_VALS=0
DOCKER="false"

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
    -d          Execute tests in Docker containers instead of in local venvs.
    -o <dir>    Collect Junit-style reports into <dir>.
    -h          Display help.
EOF
}

while getopts ":o:dh" flag; do
	case "${flag}" in
        o)
            if [[ "${OPTARG}" = /* ]]; then
                # Exported envvars auto-converted to Makefile variables
                export REPORT_PATH="${OPTARG}"
            else
                export REPORT_PATH=$(realpath "${SUITES_DIR}/${OPTARG}")
            fi
            echo "[x] JUnit-style reports are configured with path: ${REPORT_PATH}"
            echo -e "\nPreparing report folder..."
            [[ -d "${REPORT_PATH}" ]] && rm -rfv "${REPORT_PATH}"
            mkdir -pv "${REPORT_PATH}"
            ;;
        d)
            echo "[x] Docker-based unit test execution is configured."
            DOCKER="true"
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
            exit 1;;
    esac
done

echo -e "\nCollecting projects..."
mapfile -t PROJECTS < <( ls -d "${ROOT_DIR}"/src/* )
PROJECTS+=("${ROOT_DIR}/test/mock-api")
printf "  - %s\n" "${PROJECTS[@]}"

for project in "${PROJECTS[@]}"; do
    log "Entering ${project}"
    pushd "$(realpath "${project}")" >/dev/null
    if [[ "${DOCKER}" == "true" ]]; then
        make docker-unit-tests
    else
        make unit-tests
    fi
    RET_VALS=$(( "${RET_VALS}" + "$?" ))
    popd >/dev/null
done

[[ ${RET_VALS} -eq 0 ]] && exit 0 || exit 1