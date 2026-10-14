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

LOG "Test Infra Service Chain with Adapter"

_BASE_URL="https://${NGROK_DOMAIN}/datasource/pdc"

log "Initiate login..."
LOGIN_BODY=$(jq -n "$(cat <<EOF
{
    "secretKey": "${DS_PDC_SECRET_KEY}",
    "serviceKey": "${DS_PDC_SERVICE_KEY}"
}
EOF
)")

_URL="${_BASE_URL}/login"
echo "Used URL: [POST] ${_URL}"

echo -e "\nPrepared login body:"
echo "${LOGIN_BODY}" | jq

RESP=$(curl -Ssf -X POST \
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

log "Initiate infra service chain with adapter..."

EXCHANGE_BODY=$(jq -n "$(cat <<EOF
{
    "contract": "https://contract.visionstrust.com/contracts/${SC_CONTRACT_ID}",
    "serviceChainId": "${SC_CHAIN_INFRA_CONSUMER_ID}",
    "resourceId": "https://api.visionstrust.com/v1/catalog/serviceofferings/${PROVIDER_OFFER_ID}",
    "resources": [
        {
            "resource": "https://api.visionstrust.com/v1/catalog/dataresources/${PROVIDER_RESOURCE_ID}"
        }
    ],
    "purposeId": "https://api.visionstrust.com/v1/catalog/serviceofferings/${CONSUMER_OFFER_ID}",
    "purposes": [
        {
             "resource": "https://api.visionstrust.com/v1/catalog/softwareresources/${CONSUMER_RESOURCE_ID}"
        }
    ]
}
EOF
)")

_URL="${_BASE_URL}/exchange"
echo "Used URL: [POST] ${_URL}"

echo -e "\nPrepared exchange body:"
echo "${EXCHANGE_BODY}" | jq

RESP=$(curl -Ss --fail-with-body -X POST \
                                "${_URL}" \
                                -H "Content-Type: application/json" \
                                -H "Accept: application/json" \
                                -H "Authorization: Bearer ${TOKEN}" \
                                -d "${EXCHANGE_BODY}")

echo -e "\nReceived response:"
echo "${RESP}" | jq

if ! jq -e '.code' <<<"${RESP}" &>/dev/null || \
        [ "$(jq '.code' <<<"${RESP}")" -ne 200 ] || \
        [ "$(jq '.content.success' <<<"${RESP}")" != "true" ]; then
    error "Service chain request failed!" && exit 1
else
    echo -e "\nService chain execution was successful!"
fi

echo -e "\nExchange status: $(jq -r '.content.dataExchange.status' <<<"${RESP}")"

########################################################################################################################

echo -e "\nDone."