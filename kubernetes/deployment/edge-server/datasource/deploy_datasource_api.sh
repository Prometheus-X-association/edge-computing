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

DS_REPO=git@github.com:nada-a1/xapi-data-source.git
DS_API_IMG="edge-server/datasource-xapi:latest"
DS_API_NAME="xapi-data-source"
DS_PDC_LOGIN_FILE="${SCRIPT_DIR}/datasource/creds/pdc.login.token"

########################################################################################################################

function display_help() {
    cat <<EOF
Usage: ${0} [OPTIONS]

Options:
    -x  Dry run. Only perform configuration without execution.
    -f  Force and rebuild datasource configuration.
    -h  Display help.
EOF
}

DRY_RUN="false"
FORCE_RECREATE="false"

while getopts ":xfh" flag; do
	case "${flag}" in
        x)
            DRY_RUN=true;;
        f)
            FORCE_RECREATE=true;;
        h)
            display_help
            exit;;
        ?)
            echo -e "${0##*/}: invalid option -- '${OPTARG}'\nTry '${0} -h' for more information." 1>&2
            exit 1
    esac
done

########################################################################################################################

# Loaded from creds/fured-datasource-creds.sh !
### DS_API_DIR=
### DS_API_VER=

LOG "Setup Datasource API"

if [ -z "${DS_API_DIR:-}" ]; then
    DS_API_DIR=$(readlink -f "$(dirname "$0")/api")
fi
mkdir -p "${DS_API_DIR}"
echo "Used dir for datasource: ${DS_API_DIR}"
echo "Used version for datasource: ${DS_API_VER:=main}"

log "Remove remnant containers..."
pushd "${DS_API_DIR}"
    docker compose down -v || true
popd

if [ "${FORCE_RECREATE}" = "true" ] || [ ! -d "${DS_API_DIR}" ] || [ -z "$( ls -A "${DS_API_DIR}" )" ] ; then
    log "Cleanup datasource config..."
    sudo rm -rf "${DS_API_DIR}"

    log "Pull datasource with version: ${DS_API_VER}..."
    git clone "${DS_REPO}" "${DS_API_DIR}"
    pushd "${DS_API_DIR}"
        git switch --detach "${DS_API_VER}"
    popd

    if [ ! -f "${DS_PDC_LOGIN_FILE}" ]; then
        error "PDC login file does not exist!"
        exit 1
    fi

    log "Create datasource configuration..."
    cat <<-EOF >"${DS_API_DIR}/.env"
# Base URL of the PDC.
PDC_BASE_URL=http://host.docker.internal:3000

# Optional: bearer token for the PDC. Leave empty to send no Authorization header.
PDC_TOKEN=$(cat "$DS_PDC_LOGIN_FILE")

# Contract and service chain
SC_CONTRACT_ID=${SC_CONTRACT_ID:?}
SC_CHAIN_BASIC_ID=${SC_CHAIN_BASIC_ID:?}

# Catalog base URL, without a trailing slash
CATALOG_URI=${PTX_CATALOG_URI:?}

# Provider (this data source): service offering and data resource
PROVIDER_OFFER_ID=${PROVIDER_OFFER_ID:?}
PROVIDER_RESOURCE_ID=${PROVIDER_RESOURCE_ID:?}

# Consumer (the analysis service): service offering and software resource
CONSUMER_OFFER_ID=${CONSUMER_OFFER_ID:?}
CONSUMER_RESOURCE_ID=${CONSUMER_RESOURCE_ID:?}

# DATA_FILE is set in docker-compose.yml for Docker. For a local run it defaults to
# data/test_data_input_statements.json.
EOF
    ls -alht "${DS_API_DIR}/.env"
fi

# Build image
log "Build datasource image..."
    pushd "${DS_API_DIR}"
        docker compose build
    popd
docker image ls "${DS_API_IMG}"

if [ "${DRY_RUN}" = "true" ]; then
    exit 0
fi

########################################################################################################################

log "Start datasource container..."
pushd "${DS_API_DIR}"
    docker compose down -v && docker compose up -d --no-build --force-recreate
popd

log "Waiting for completed startup..."
sleep 3
# Wait for server startup
(docker logs -f -t "${DS_API_NAME}" 2>&1 &) | timeout "${TIMEOUT}" grep -B5 -m1 "Application startup complete."
# shellcheck disable=SC2181
if [ "${?}" -ne 0 ]; then
    error "${DS_API_NAME} failed!"
    docker logs "${DS_API_NAME}"
    exit 1
else
    echo -e "\n${DS_API_NAME} is initiated successfully!"
fi

log "Datasource API is exposed on http://${GW_DOMAIN}:${GW_PORT}/"

########################################################################################################################

echo -e "\nDone."