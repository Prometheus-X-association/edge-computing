#!/usr/bin/env bash
# Copyright 2026 Janos Czentye
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

# Loaded from creds/fured-cloud-creds.sh !
### DS_NGROK_AUTHTOKEN=
### DS_NGROK_DOMAIN=
NAME_PREFIX="ngrok-tun"
TARGET_PORT="${1}"

########################################################################################################################

LOG "Initiate NGROK tunnel"

if [ "${USE_NGROK}" == "false" ]; then
    if [ -v DS_NGROK_AUTHTOKEN ] && [ -v DS_NGROK_DOMAIN ]; then
        warning "NGROK tunneling is disabled while NGROK creds are given! Skip tunnel creation anyway..."
    fi
    exit 0
fi

log "Remove still running containers..."
# Shut down running instance
#docker rm --force "${NAME_PREFIX}" || true
docker ps -aq -f name="${NAME_PREFIX}-*" | xargs -r docker rm --force || true

log "Start tunnel to port: ${TARGET_PORT}..."
CONTAINER_NAME="${NAME_PREFIX}-$(echo "${TARGET_PORT}" | grep -P -o ':?\K\d+$')"
# Run ngrok tunnel
docker run -d --net=host \
        -e NGROK_AUTHTOKEN="${DS_NGROK_AUTHTOKEN}" \
        --name "${CONTAINER_NAME}" \
        --label "${LAB_ROLE}=datasource" \
        ngrok/ngrok:latest \
        http "${TARGET_PORT}" --url="${DS_NGROK_DOMAIN}" --log=stdout
#docker run --rm --net=host --name ngrok-tunnel -e NGROK_AUTHTOKEN=${DS_NGROK_AUTHTOKEN} -it ngrok/ngrok:latest \
#http --url=crux-rented-delirious.ngrok-free.dev 9080

log "Waiting for completed startup..."
# Wait for server startup
#sleep 3
(docker logs -t -f "${CONTAINER_NAME}" 2>&1 &) | timeout "${TIMEOUT}" grep -B5 -m1 "started tunnel" || true

if [ "$(docker container inspect -f '{{.State.Status}}' "${CONTAINER_NAME}")" == "running" ]; then
    log "Port: ${TARGET_PORT} is exposed on https://${DS_NGROK_DOMAIN}/"
else
    error "NGROK container creation failed!"
    docker logs "${CONTAINER_NAME}"
    exit 1
fi

########################################################################################################################

echo -e "\nDone."