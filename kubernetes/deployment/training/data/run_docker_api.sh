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
set -eou pipefail

IMG="training/data-api:latest"
NAME="training-data-api"
#
PORT=8443
DOMAIN="datasource.ptx.localhost"
#
USERNAME="admin"
PASSWORD="datasource1234"

# Build image
docker build -t "${IMG}" --build-arg PORT="${PORT}" --build-arg DOMAIN="${DOMAIN}" .
docker image ls "${IMG}"
docker rm --force "${NAME}" || true
docker run -d -p "${PORT}:${PORT}" -v "./resource:/usr/src/api/resource" -e USERNAME="${USERNAME}" -e PASSWORD="${PASSWORD}" \
    --name "${NAME}" "${IMG}"
docker ps -l
sleep 1 && docker logs "${NAME}"
