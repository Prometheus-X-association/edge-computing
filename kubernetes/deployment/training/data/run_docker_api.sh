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

source "$(readlink -f "$(dirname "$0")/../cfg/config.sh")"

########################################################################################################################

# Datasource image config
DATASOURCE_IMG="training/data-api:latest"
DATASOURCE_API_NAME="training-data-api"
DATASOURCE_PORT=9443
# Datasource API config
# Loaded from creds/websecure-creds.sh !
### DATASOURCE_API_DOMAIN=
### DATASOURCE_USERNAME=
### DATASOURCE_PASSWORD=

########################################################################################################################

LOG "Initiate Datasource API..."

# Create certs
rm -rf "${SCRIPT_DIR}/data/cert/" && mkdir -pv "${SCRIPT_DIR}/data/cert/"
pushd "${SCRIPT_DIR}/data/cert/"
    openssl req -newkey rsa:4096 -noenc -keyout api-tls.key -out api-tls.csr \
        -subj "/C=EU/O=PTX/OU=edge/CN=${DATASOURCE_API_DOMAIN}" -reqexts SAN \
        -config <(printf "[SAN]\nsubjectAltName=DNS:%s,DNS:%s" "${DATASOURCE_API_DOMAIN}" "datasource.ptx.localhost")
    openssl x509 -req -days 365 -in api-tls.csr -CA "${CA_DIR}/ca.crt" -CAkey "${CA_DIR}/../ca.key" \
        -out api-tls.cert -CAcreateserial -extensions SAN \
        -extfile <(printf "[SAN]\nsubjectAltName=DNS:%s,DNS:%s" "${DATASOURCE_API_DOMAIN}" "datasource.ptx.localhost")
    openssl x509 -in api-tls.cert -noout -text
popd

# Build image
docker build -t "${DATASOURCE_IMG}" --build-arg DOMAIN="${DATASOURCE_API_DOMAIN}" .
docker image ls "${DATASOURCE_IMG}"

# Shut down running instance
docker rm --force "${DATASOURCE_API_NAME}" || true

# Run datasource API server
docker run -d -p "${DATASOURCE_PORT}:4443" -e USERNAME="${DATASOURCE_USERNAME}" -e PASSWORD="${DATASOURCE_PASSWORD}" \
    -v "./resource:/usr/src/api/resource" --name "${DATASOURCE_API_NAME}" "${DATASOURCE_IMG}"

# Check running instance
docker ps -l && sleep 1 && docker logs "${DATASOURCE_API_NAME}" -f
