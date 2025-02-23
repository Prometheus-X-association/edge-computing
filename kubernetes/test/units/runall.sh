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

ROOT_DIR=$(readlink -f "$(dirname "$0")/../..")
RET_VALS=0

source "${ROOT_DIR}"/test/scripts/helper.sh

function sig_handler(){
    echo "Signal caught. Exiting from tests..."
    exit 1
}

trap sig_handler INT TERM

echo "Collecting projects..."
mapfile -t PROJECTS < <( ls -d "${ROOT_DIR}"/src/* )
PROJECTS+=("${ROOT_DIR}/test/mock-api")
printf "  - %s\n" "${PROJECTS[@]}"

for project in "${PROJECTS[@]}"; do
    log "Entering ${project}"
    pushd "$(realpath "${project}")" >/dev/null
    make unit-tests
    RET_VALS=$(( "${RET_VALS}" + "$?" ))
    popd >/dev/null
done

[[ ${RET_VALS} -eq 0 ]] && exit 0 || exit 1