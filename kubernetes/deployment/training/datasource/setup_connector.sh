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

PDC_REPO=https://github.com/Prometheus-X-association/dataspace-connector.git
DS_PDC_LOGIN_FILE="${SCRIPT_DIR}/datasource/creds/pdc.login.token"

########################################################################################################################

function display_help() {
    cat <<EOF
Usage: ${0} [OPTIONS]

Options:
    -x  Dry run. Only perform configuration without execution.
    -h  Display help.
EOF
}

DRY_RUN="false"

while getopts ":xh" flag; do
	case "${flag}" in
        x)
            DRY_RUN=true;;
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
### DS_PDC_DIR=
### DS_PDC_VER=

LOG "Setup Dataspace Connector (PDC)"

if [ -z "${DS_PDC_DIR:-}" ]; then
    DS_PDC_DIR=$(readlink -f "$(dirname "$0")/pdc")
fi
mkdir -p "${DS_PDC_DIR}"
echo "Used dir for PDC: ${DS_PDC_DIR}"

log "Remove remnant containers..."
pushd "${DS_PDC_DIR}"
    docker compose down -v || true
popd
sudo rm -rf "${DS_PDC_DIR}"

log "Pull PDC source with version: ${DS_PDC_VER}..."
git clone "${PDC_REPO}" "${DS_PDC_DIR}"
pushd "${DS_PDC_DIR}"
    git switch --detach "v${DS_PDC_VER}"
popd


log "Adjust docker setup.."
cat <<'EOF' >"${DS_PDC_DIR}/docker/app/Dockerfile"
# Use the official Node.js image as base image
FROM node:22
ARG ENV
ENV ENV $ENV
LABEL role.dataspace.ptx.org="datasource"

# Install pnpm globally
RUN npm install -g pnpm@9.15.5

# Create app directory
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY package.json .

## Bundle app source
COPY . .

RUN chmod +x ./docker/scripts/start.sh

RUN rm -f node_modules
RUN rm -f /src/logs

RUN mkdir -p /src/logs
RUN mkdir -p /src/keys

# Install app dependencies
RUN pnpm install --frozen-lockfile --ignore-scripts

# Expose the port on which the app will run
EXPOSE 3000

CMD ["./docker/scripts/start.sh", "$ENV"]
EOF
ls -alht "${DS_PDC_DIR}/docker/app/Dockerfile"

if [ "${USE_NGROK}" = "false" ]; then
    if [ -v NGROK_AUTHTOKEN ] && [ -v NGROK_DOMAIN ]; then
        warning """NGROK creds are given without enabling NGROK tunneling! Either enable it to bind it localhost or disable explicitly."
    fi
    EXPOSED_PORT="3000"
else
    EXPOSED_PORT="127.0.0.1:3000"
fi

cat <<'EOF' >"${DS_PDC_DIR}/docker-compose.yml"
services:
  dataspace-connector:
    container_name: dataspace-connector
    build:
      context: .
      dockerfile: docker/app/Dockerfile
      args:
        ENV: ${NODE_ENV}
    labels:
      role.dataspace.ptx.org: datasource
    restart: unless-stopped
    tty: true
    volumes:
      - "./src/config.json/:/usr/src/app/src/config.json"
    ports:
      - "${EXPOSED_PORT}:${PORT}"
    environment:
      MONGO_URI: ${MONGO_URI}
    depends_on:
      - mongodb
    networks:
      - dataspace-connector

  mongodb:
    container_name: mongodb
    image: mongo:latest
    labels:
      role.dataspace.ptx.org: datasource
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_INITDB_ROOT_USERNAME}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
      MONGO_INITDB_DATABASE: dataspace-connector
    restart: unless-stopped
    volumes:
      - "./data:/data/db"
      - "./mongo-init.js:/docker-entrypoint-initdb.d/mongo-init.js:ro"
    networks:
      - dataspace-connector

networks:
  dataspace-connector:
    external: false
EOF
ls -alht "${DS_PDC_DIR}/docker-compose.yml"


# Loaded from creds/0-default-config.sh !
### PTX_*=
# Loaded from creds/fured-datasource-creds.sh !
### DS_PDC_*=

log "Create config files.."
cat <<EOF >"${DS_PDC_DIR}/src/config.json"
{
    "endpoint": "${DS_PDC_ENDPOINT}",
    "serviceKey": "${DS_PDC_SERVICE_KEY}",
    "secretKey": "${DS_PDC_SECRET_KEY}",
    "catalogUri": "${PTX_CATALOG_URI}",
    "contractUri": "${PTX_CONTRACT_URI}",
    "consentUri": "${PTX_CONSENT_URI}",
    "expressLimitSize": "10mb",
    "serviceChainAdapter": false,
    "serviceChainAdapterTimeout": 3000
}
EOF
ls -alht "${DS_PDC_DIR}/src/config.json"

# Loaded from creds/0-default-config.sh !
### PDC_ENV=
### PDC_PORT=
# Loaded from creds/fured-datasource-creds.sh !
### DS_PDC_*=
### DS_MONGO_*=

cat <<EOF >"${DS_PDC_DIR}/.env"
NODE_ENV=${PDC_ENV}
PORT=${PDC_PORT}
EXPOSED_PORT=${EXPOSED_PORT}

SESSION_SECRET=$(openssl rand -base64 32 | tr -d /=+ | cut -c -16)
SESSION_COOKIE_EXPIRATION=24000

MONGO_URI=mongodb://${DS_PDC_DB_USER}:${DS_PDC_DB_PASSWORD}@mongodb:27017/${DS_PDC_DB_NAME}?authSource=${DS_PDC_DB_NAME}
MONGO_INITDB_ROOT_USERNAME=${DS_MONGO_INITDB_ROOT_USERNAME}
MONGO_INITDB_ROOT_PASSWORD=${DS_MONGO_INITDB_ROOT_PASSWORD}

CURATOR=https://visionspol.eu
MAINTAINER=https://visionspol.eu

# Logs
WINSTON_LOGS_MAX_FILES=14d
WINSTON_LOGS_MAX_SIZE=20m

#jwt
JWT_BEARER_TOKEN_EXPIRATION=3h
JWT_REFRESH_TOKEN_EXPIRATION=1d

# Exchange Trigger
EXCHANGE_TRIGGER_API_KEY=${DS_PDC_EXCHANGE_TRIGGER_API_KEY}

# Exchange Timeout in seconds
EXCHANGE_TIMEOUT=120
EOF
ls -alht "${DS_PDC_DIR}/.env"

# Loaded from creds/fured-datasource-creds.sh !
### DS_PDC_*=

cat <<EOF >"${DS_PDC_DIR}/mongo-init.js"
db = db.getSiblingDB('${DS_PDC_DB_NAME}');
db.createUser({
    user: '${DS_PDC_DB_USER}',
    pwd: '${DS_PDC_DB_PASSWORD}',
    roles: [{ role: 'readWrite', db: '${DS_PDC_DB_NAME}' }]
});
EOF
ls -alht "${DS_PDC_DIR}/mongo-init.js"


log "Build PDC..."
cd "${DS_PDC_DIR}"
docker compose build

if [ "${DRY_RUN}" = "true" ]; then
    exit 0
fi

log "Start PDC..."
docker compose up -d

log "Waiting for PDC instance to set up..."
( docker logs "dataspace-connector" -t -f 2>&1 & ) | timeout "${TIMEOUT}" grep -m1 "Server running on"
if [ "${?}" -ne 0 ]; then
    error "PDC failed!"
    docker logs "dataspace-connector"
    exit 1
fi

log "Validating connector..."
LOGIN_BODY=$(jq -n --arg secret "${DS_PDC_SECRET_KEY}" \
                   --arg service "${DS_PDC_SERVICE_KEY}" \
                   '{secretKey: $secret, serviceKey: $service}')

RESP=$(curl -sX POST http://localhost:3000/login \
             -H "Content-Type: application/json" \
             -d "${LOGIN_BODY}")

if [ "$(jq '.code' <<<"${RESP}")" -ne 200 ]; then
    log "Login request failed!"
    echo "${RESP}" | jq
    exit 1
else
    TOKEN=$(jq -r '.content.token' <<<"${RESP}")
    echo "${TOKEN}" >"${DS_PDC_LOGIN_FILE}"
    log "Login was successful! Received bearer token: ${TOKEN}"
fi

echo -e "\nDone."