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

########################################################################################################################

# Datasource image config
DATASOURCE_IMG="training/data-api:latest"
DATASOURCE_API_NAME="training-data-api"

# Datasource API config
# Loaded from creds/fured-cloud-creds.sh !
### DS_API_USER=
### DS_API_PASSWORD=
### GW_DOMAIN=
### GW_PORT=
TIMEOUT=5

########################################################################################################################

function display_help() {
    cat <<EOF
Usage: ${0} [OPTIONS]

Options:
    -s  Run secured API with HTTPS.
    -h  Display help.
EOF
}

TLS_ENABLED="false"

while getopts ":sh" flag; do
	case "${flag}" in
        s)
            TLS_ENABLED=true;;
        h)
            display_help
            exit;;
        ?)
            echo -e "${0##*/}: invalid option -- '${OPTARG}'\nTry '${0} -h' for more information." 1>&2
            exit 1
    esac
done

########################################################################################################################

LOG "Initiate Datasource API for domain: ${GW_DOMAIN}"

if [ "${TLS_ENABLED}" == "true" ]; then
    # Create certs
    rm -rf "${SCRIPT_DIR}/datasource/cert/" && mkdir -pv "${SCRIPT_DIR}/datasource/cert/"
    pushd "${SCRIPT_DIR}/datasource/cert/"
        if [ -e "${ROOT_DIR}/src/registry" ]; then
            if [ ! -f "${CA_DIR}/ca.crt" ]; then
                log "No CA cert detected in ${CA_DIR}! Generate it manually..."
                pushd "${ROOT_DIR}/src/registry"
                    # Generate CA
                    make ca
                popd
                log "Cache used registry CA files locally"
                mkdir -p "${SCRIPT_DIR}/creds/cert/ca"
                cp -vR "${ROOT_DIR}/src/registry/.certs/ca/ca.crt" "${SCRIPT_DIR}/creds/cert/ca/ca.crt"
                cp -vR "${ROOT_DIR}/src/registry/.certs/ca.key" "${SCRIPT_DIR}/creds/cert/ca.key"
            fi
            log "Generate server cert..."
            # Create signing request
            openssl req -newkey rsa:4096 -noenc -keyout api-tls.key -out api-tls.csr \
                -subj "/C=EU/O=PTX/OU=edge/CN=${GW_DOMAIN}" -reqexts SAN \
                -config <(printf "[SAN]\nsubjectAltName=DNS:%s,DNS:%s" "${GW_DOMAIN}" "datasource.ptx.localhost")
            # Generate cert
            openssl x509 -req -days 365 -in api-tls.csr -CA "${CA_DIR}/ca.crt" -CAkey "${CA_DIR}/../ca.key" \
                -out api-tls.cert -CAcreateserial -extensions SAN \
                -extfile <(printf "[SAN]\nsubjectAltName=DNS:%s,DNS:%s" "${GW_DOMAIN}" "datasource.ptx.localhost")
            # Validate
            log "Validated server cert"
            openssl x509 -in api-tls.cert -noout -ext subjectAltName
        else
            log "No registry project detected! Generate self-signed cert..."
            # Generate self-signed cert
            openssl req -x509 -noenc -days 365 -newkey rsa:4096 -subj "/C=EU/O=PTX/OU=dataspace/CN=${GW_DOMAIN}" \
                                                        -keyout api-tls.key -out api-tls.cert
        fi
    popd
fi

# Build image
log "Build image..."
docker build -t "${DATASOURCE_IMG}" --build-arg DOMAIN="${GW_DOMAIN}" .
docker image ls "${DATASOURCE_IMG}"

log "Remove running container..."
# Shut down running instance
docker rm --force "${DATASOURCE_API_NAME}" || true

if [ "${TLS_ENABLED}" == "true" ]; then
    DATASOURCE_PORT=9443
    SSL_ARG=(
        '--ssl-keyfile=cert/api-tls.key'
        '--ssl-certfile=cert/api-tls.cert')
else
    DATASOURCE_PORT=9080
fi

log "Start datasource API on port: ${DATASOURCE_PORT}..."
# Run datasource API server
docker run -d -p "${DATASOURCE_PORT}:8888" \
        -e USERNAME="${DS_API_USER}" \
        -e PASSWORD="${DS_API_PASSWORD}" \
        -e GW_DOMAIN="${GW_DOMAIN}" \
        -e GW_PORT="${GW_PORT}" \
        -v "./resource:/usr/src/api/resource:ro" \
        --name "${DATASOURCE_API_NAME}" \
        --label "${LAB_ROLE}=datasource" \
        "${DATASOURCE_IMG}" \
        "${SSL_ARG[@]}" # Expand ssl args to uvicorn inside container, otherwise skip parameter entirely

# Check running instance
docker ps --no-trunc -l && sleep 1

log "Waiting for completed startup..."
# Wait for server startup
(docker logs -f -t "${DATASOURCE_API_NAME}" 2>&1 &) | timeout "${TIMEOUT}" grep -B5 -m1 "Application startup complete."