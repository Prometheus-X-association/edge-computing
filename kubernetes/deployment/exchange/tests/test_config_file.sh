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

ROOT_DIR=$(readlink -f "$(dirname "${BASH_SOURCE[0]}")/..")
source "${ROOT_DIR}/scripts/helper.sh"
source "${ROOT_DIR}/creds/exchange.env"

########################################################################################################################

LOG "Test Configuration file"

_BASE_URL="https://${NGROK_DOMAIN}/service/pdc"

log "Initiate login..."
LOGIN_BODY=$(jq -n "$(cat <<EOF
{
    "secretKey": "${PDC_SECRET_KEY}",
    "serviceKey": "${PDC_SERVICE_KEY}"
}
EOF
)")

echo -e "\nPrepared login body:"
echo "${LOGIN_BODY}" | jq

_URL="${_BASE_URL}/login"
echo -e "\nUsed URL: [POST] ${_URL}"

RESP=$(curl -Ss -X POST \
                "${_URL}" \
                -H "Content-Type: application/json" \
                -H "Accept: application/json" \
                -d "${LOGIN_BODY}")

echo -e "\nReceived response:"
echo "${RESP}" | jq

if ! jq -e '.code' <<<"${RESP}" &>/dev/null || [ "$(jq '.code' <<<"${RESP}")" -ne 200 ]; then
    error "Login request failed!" && exit 1
else
    TOKEN=$(jq -r '.content.token' <<<"${RESP}")
    echo "${TOKEN}" >creds/consumer.login.token
    echo -e "\nLogin was successful!"
fi

echo -e "\nBearer token: ${TOKEN}"

########################################################################################################################

log "Request PDC configuration..."

_URL="${_BASE_URL}/private/configuration"
echo "Used URL: [GET] ${_URL}"

RESP=$(curl -Ss -X GET \
                "${_URL}" \
                -H "Accept: application/json" \
                -H "Authorization: Bearer ${TOKEN}")

echo -e "\nReceived response:"
echo "${RESP}" | jq

if ! jq -e '.code' <<<"${RESP}" >/dev/null || [ "$(jq '.code' <<<"${RESP}")" -ne 200 ]; then
    error "Config config failed!" && exit 1
else
    echo -e "\nConfig request was successful!"
fi

########################################################################################################################

log "Adjust PDC configuration..."

docker exec -ti pdc-consumer \
    sed -i -e "/endpoint/c\  \"endpoint\": \"https://${NGROK_DOMAIN}/service/pdc/v1/\"," \
    src/config.development.json

echo -e "\nOverwritten config file:"
# shellcheck disable=SC2005
echo "$(docker exec -ti pdc-consumer cat src/config.development.json)" | jq

########################################################################################################################

log "Reload PDC..."

_URL="${_BASE_URL}/private/configuration/reload"
echo "Used URL: [POST] ${_URL}"

RESP=$(curl -Ss -X POST \
                "${_URL}" \
                -H "Accept: application/json" \
                -H "Authorization: Bearer ${TOKEN}")

echo -e "\nReceived response:"
echo "${RESP}" | jq

if ! jq -e '.code' <<<"${RESP}" >/dev/null || [ "$(jq '.code' <<<"${RESP}")" -ne 200 ]; then
    error "Config reload failed!" && exit 1
else
    echo -e "\nConfig reload was successful!"
fi

########################################################################################################################

log "Restart PDC container..."

docker restart pdc-consumer
( docker logs pdc-consumer -f & ) | timeout 20 grep -m1 "Server running on"
sleep 3

########################################################################################################################

log "Test configuration after PDC restart..."

_URL="${_BASE_URL}/private/configuration"
echo "Used URL: [GET] ${_URL}"

RESP=$(curl -s --retry 5 --retry-all-errors --retry-connrefused --retry-delay 3 --no-progress-meter \
                                                                                -X GET \
                                                                                "${_URL}" \
                                                                                -H "Accept: application/json" \
                                                                                -H "Authorization: Bearer ${TOKEN}"\
                                                                                )

echo -e "\nReceived response:"
echo "${RESP}" | jq

if ! jq -e '.code' <<<"${RESP}" >/dev/null || [ "$(jq '.code' <<<"${RESP}")" -ne 200 ]; then
    error "Config reload failed!" && exit 1
else
    echo -e "\nConfig reload was successful!"
fi

########################################################################################################################

echo -e "\nDone."