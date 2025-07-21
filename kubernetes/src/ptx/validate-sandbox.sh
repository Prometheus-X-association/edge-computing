#!/usr/bin/env bash
# Copyright 2025 Janos Czentye
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

#PDC_IP=$(kubectl get pod -l app=pdc -o jsonpath='{.items[].status.hostIP}')
#PDC_PORT=30030

PDC_IP="127.0.0.1"
PDC_PORT=3011

PDC_SECRET_KEY=Qh4XvuhSJbOp8nMV1JtibAUqjp3w_efBeFUfCmqQW_Nl8x4t3Sk6fWiK5L05CB3jhKZOgY5JlBSvWkFBHH_6fFhYQZWXNoZxO78x
PDC_SERVICE_KEY=dWJUUKH9rYF9wr_UAPb6PQXW9h17G7dzuGCbiDhcyjCGgHzLwBp6QHOQhDg0FFxS24GD8nvw37oe_LOjl7ztNATYiVOd_ZEVHQpV

PDC_LOGIN_FILE=".pdc.login.json"
########################################################################################################################

echo """
============================= Validate Sandbox =============================

PDC node IP: ${PDC_IP}
PDC node port: ${PDC_PORT}

OpenAPI docs available at http://${PDC_IP}:${PDC_PORT}/docs
"""

########################################################################################################################

if [ ! -e "${PDC_LOGIN_FILE}" ]; then
    echo -e "\n>>> RUN /login"

    BODY=$(jq -n --arg secret "${PDC_SECRET_KEY}" --arg service "${PDC_SERVICE_KEY}" \
            '{secretKey: $secret, serviceKey: $service}')
    echo -e "\n>>> Prepared request:"
    echo "${BODY}"

    RES=$(curl -sX POST "http://${PDC_IP}:${PDC_PORT}/login" \
        -H 'accept: application/json' -H 'Content-Type: application/json' \
        -d "${BODY}")

    echo
    if [[ $(jq '.code' <<<"${RES}") -ne 200 ]]; then
        echo -e "\n>>> Login request failed!"
        echo "${RES}" | jq
        exit 1
    else
        echo -e "\n>>> Login was successful!"
        echo "${RES}" > "${PDC_LOGIN_FILE}"
    fi
    TOKEN=$(jq -r '.content.token' <<<"${RES}")
    echo -e "\nExtracted Bearer token: ${TOKEN}"
else
    echo -e "\n>>> Loading cached login response..."
    TOKEN=$(jq -r '.content.token' <"${PDC_LOGIN_FILE}")
    echo -e "\n>>> Validating Bearer token..."
    RET=$(curl -SsLv -o /dev/null -w '%{http_code}' "http:/${PDC_IP}:${PDC_PORT}/private/configuration/" \
                                                            -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}")
    if [[ "${RET}" -ne 200 ]]; then
        echo -e "\n>>> Invalid token! Removing cached response..."
        rm -f "${PDC_LOGIN_FILE}"
        exit 0
    fi
fi

########################################################################################################################

echo
echo "============================= Check PDC private API ============================="

ENDPOINT="/private/configuration/"
echo -e "\n>>> RUN ${ENDPOINT}"
curl -sX GET "http://${PDC_IP}:${PDC_PORT}${ENDPOINT}" \
    -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}" | jq

ENDPOINT="/private/catalogs/"
echo -e "\n>>> RUN ${ENDPOINT}"
curl -sX GET "http://${PDC_IP}:${PDC_PORT}${ENDPOINT}" \
    -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}" | jq

ENDPOINT="/private/credentials/"
echo -e "\n>>> RUN ${ENDPOINT}"
curl -sX GET "http://${PDC_IP}:${PDC_PORT}${ENDPOINT}" \
    -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}" | jq

ENDPOINT="/private/infrastructure/configurations/"
echo -e "\n>>> RUN ${ENDPOINT}"
curl -sX GET "http://${PDC_IP}:${PDC_PORT}${ENDPOINT}" \
    -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}" | jq

ENDPOINT="/private/users/"
echo -e "\n>>> RUN ${ENDPOINT}"
curl -sX GET "http://${PDC_IP}:${PDC_PORT}${ENDPOINT}" \
    -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}" | jq

########################################################################################################################

CONTRACT_IP="127.0.0.1"
CONTRACT_PORT=3001

echo
echo "============================= Check Contract API ============================="

contractID=672c89942308b486f7d0bca1
#contractID=66db1a6dc29e3ba863a85e0f
echo -e "\n>>> Using contract id: ${contractID}"

contract=$(curl -Ssf "http://${CONTRACT_IP}:${CONTRACT_PORT}/contracts/${contractID}")
echo "${contract}" | jq

########################################################################################################################

echo
echo "============================= Check Catalog API - provider ============================="

CATALOG_IP="127.0.0.1"
CATALOG_PORT=3002

providerID=66d18724ee71f9f096bae810 # orchestrator / provider
providerOfferID=672c89cb870a096712ca4d59
providerDataID=672c8a28870a096712ca4e63

echo -e "\n >>> Check provider: ${providerID}"
provider=$(curl -Ssf "http://${CATALOG_IP}:${CATALOG_PORT}/v1/catalog/participants/${providerID}")
echo "${provider}" | jq

echo -e "\n >>> Check provider offer: ${providerOfferID}"
providerOffer=$(curl -Ssf "http://${CATALOG_IP}:${CATALOG_PORT}/v1/catalog/serviceofferings/${providerOfferID}")
echo "${providerOffer}" | jq

echo -e "\n >>> Check provider data: ${providerDataID}"
providerData=$(curl -Ssf "http://${CATALOG_IP}:${CATALOG_PORT}/v1/catalog/dataresources/${providerDataID}")
echo "${providerData}" | jq

########################################################################################################################

echo
echo "============================= Check Catalog API - consumer ============================="

consumerID=66d18a1dee71f9f096baec08 # participant / consumer
consumerOfferID=672c8ae4870a096712ca56d7
consumerSoftwareID=672c8acc870a096712ca565d

echo -e "\n >>> Check consumer: ${consumerID}"
consumer=$(curl -Ssf "http://${CATALOG_IP}:${CATALOG_PORT}/v1/catalog/participants/${consumerID}")
echo "${consumer}" | jq

echo -e "\n >>> Check consumer offer: ${consumerOfferID}"
consumerOffer=$(curl -Ssf "http://${CATALOG_IP}:${CATALOG_PORT}/v1/catalog/serviceofferings/${consumerOfferID}")
echo "${consumerOffer}" | jq

echo -e "\n >>> Check consumer software: ${consumerSoftwareID}"
consumerSoftware=$(curl -Ssf "http://${CATALOG_IP}:${CATALOG_PORT}/v1/catalog/softwareresources/${consumerSoftwareID}")
echo "${consumerSoftware}" | jq