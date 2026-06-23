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
set -euo pipefail

source "$(readlink -f "$(dirname "$0")/../cfg/config.sh")"

#python3 -m http.server --bind='0.0.0.0' --directory="$(dirname "${0}")/${FILES}" 8888

########################################################################################################################

FILES="${1:-descriptor}"
SIMPLE_API_NAME="simple-api"
SIMPLE_API_PORT=9888
DS_API_PREFIX="dataset"

########################################################################################################################

LOG "Initiate Simple API for descriptors"

log "Remove remnant container..."
# Shut down running instance
docker rm --force "${SIMPLE_API_NAME}" || true

log "Check existing PDC network..."
if docker network inspect 'pdc_dataspace-connector' >/dev/null; then
    NW_SETUP="-p 127.0.0.1:${SIMPLE_API_PORT}:8080 --network pdc_dataspace-connector"
else
    NW_SETUP="-p ${SIMPLE_API_PORT}:8080"
fi

log "Generate resource descriptors..."

for tmp in "${SCRIPT_DIR}"/datasource/descriptor/*.tmp; do
    envsubst <"${tmp}" >"${tmp%.*}"
done
ls -alth "${SCRIPT_DIR}"/datasource/descriptor/*.json

log "Start simple API on port: ${SIMPLE_API_PORT}..."
# Run datasource API server
# shellcheck disable=SC2086
docker run -d \
        ${NW_SETUP} \
        -v "${SCRIPT_DIR}/datasource/httpd.conf:/etc/httpd.conf:ro" \
        -v "./${FILES}:/usr/src/api/descriptor:ro" \
        --name "${SIMPLE_API_NAME}" \
        --label "${LAB_ROLE}=datasource" \
        busybox:latest \
        httpd -vv -f -p 0.0.0.0:8080 -h "/usr/src/api"

log "Waiting for completed startup..."
# Wait for server startup
sleep 2

if [ "$(docker container inspect -f '{{.State.Status}}' "${SIMPLE_API_NAME}")" != "running" ]; then
    error "${SIMPLE_API_NAME} failed!"
    docker logs "${SIMPLE_API_NAME}"
    exit 1
else
    echo "${SIMPLE_API_NAME} is initiated successfully!"
fi

echo -e "\nDone."
