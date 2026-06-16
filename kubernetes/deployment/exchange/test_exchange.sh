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

source creds/test-exchange.env

########################################################################################################################

echo -e "Test exchange...\n"

LOGIN_BODY=$(jq -n "$(cat <<EOF
{
    "secretKey": "${PDC_SECRET_KEY}",
    "serviceKey": "${PDC_SERVICE_KEY}"
}
EOF
)")

echo -e "Prepared login body:"
echo -e "${LOGIN_BODY}"

RESP=$(curl -s -X POST "https://${NGROK_DOMAIN}/login" \
                 -H "Content-Type: application/json" \
                 -d "${LOGIN_BODY}")

if [ "$(jq '.code' <<<"${RESP}")" -ne 200 ]; then
    echo -e "\nLogin request failed!"
    echo "${RESP}" | jq
    exit 1
else
    TOKEN=$(jq -r '.content.token' <<<"${RESP}")
    echo "${TOKEN}" >creds/consumer.login.token
    echo -e "\nLogin was successful!"
fi

echo -e "\nReceived bearer token: ${TOKEN}"

########################################################################################################################

RESP=$(curl -s -X GET "https://${NGROK_DOMAIN}/private/configuration" \
                 -H "Content-Type: application/json" \
                 -H "Authorization: Bearer ${TOKEN}")

echo -e "\nReceived PDC configuration:"
echo -e "${RESP}"

########################################################################################################################

EXCHANGE_BODY=$(jq -n "$(cat <<EOF
{
    "contract": "https://contract.visionstrust.com/contracts/${CONTRACT_ID}",
    "purposeId": "https://api.visionstrust.com/v1/catalog/serviceofferings/${CONSUMER_OFFER_ID}",
    "resourceId": "https://api.visionstrust.com/v1/catalog/serviceofferings/${PROVIDER_OFFER_ID}",
    "resources": [
        {
            "resource": "https://api.visionstrust.com/v1/catalog/dataresources/${PROVIDER_DATA_TXT_ID}"
        }
    ],
    "purposes": [
        {
             "resource": "https://api.visionstrust.com/v1/catalog/softwareresources/${CONSUMER_URL_TXT_ID}"
        }
    ]
}
EOF
)")

echo -e "\nPrepared exchange body:"
echo -e "${EXCHANGE_BODY}"

RESP=$(curl -s -X POST "https://${NGROK_DOMAIN}/consumer/exchange" \
                 -H "Content-Type: application/json" \
                 -H "Authorization: Bearer ${TOKEN}" \
                 -d "${EXCHANGE_BODY}")

echo -e "\nReceived exchange response:"
echo "${RESP}"

echo -e "\nDone."