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
### NGROK_AUTHTOKEN=
### NGROK_DOMAIN=
NAME_PREFIX="ngrok-tun"
TARGET_PORT="${1}"

########################################################################################################################

LOG "Initiate NGROK tunnel"

log "Remove running container..."
# Shut down running instance
#docker rm --force "${NAME_PREFIX}" || true
docker ps -aq -f name="${NAME_PREFIX}-*" | xargs -r docker rm --force || true

log "Start tunnel to port: ${TARGET_PORT}..."
# Run ngrok tunnel
docker run -d --net=host \
        -e NGROK_AUTHTOKEN="${NGROK_AUTHTOKEN}" \
        --name "${NAME_PREFIX}-$(echo "${TARGET_PORT}" | grep -P -o ':?\K\d+$')" \
        --label "${LAB_ROLE}=datasource" \
        ngrok/ngrok:latest \
        http \
        --url="${NGROK_DOMAIN}" \
        "${TARGET_PORT}"
#docker run --rm --net=host --name ngrok-tunnel -e NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN} -it ngrok/ngrok:latest \
#http --url=crux-rented-delirious.ngrok-free.dev 9080

# Check running instance
docker ps --no-trunc -l && sleep 1

log "Waiting for completed startup..."
# Wait for server startup
sleep 2

echo "Port: ${TARGET_PORT} is exposed on https://${NGROK_DOMAIN}/"