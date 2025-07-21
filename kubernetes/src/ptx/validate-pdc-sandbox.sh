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

#PDC_NODE_IP=$(kubectl get pod -l app=pdc -o jsonpath='{.items[].status.hostIP}')
#PDC_NODE_PORT=30030

PDC_NODE_IP="127.0.0.1"
PDC_NODE_PORT=3011

PDC_SECRET_KEY=Qh4XvuhSJbOp8nMV1JtibAUqjp3w_efBeFUfCmqQW_Nl8x4t3Sk6fWiK5L05CB3jhKZOgY5JlBSvWkFBHH_6fFhYQZWXNoZxO78x
PDC_SERVICE_KEY=dWJUUKH9rYF9wr_UAPb6PQXW9h17G7dzuGCbiDhcyjCGgHzLwBp6QHOQhDg0FFxS24GD8nvw37oe_LOjl7ztNATYiVOd_ZEVHQpV

echo
echo "PDC node IP: ${PDC_NODE_IP}"
echo "PDC node port: ${PDC_NODE_PORT}"
echo
echo "OpenAPI docs available at http://${PDC_NODE_IP}:${PDC_NODE_PORT}/docs"

if [ ! -e .pdc.login.json ]; then
    echo -e "\n>>> RUN /login"

    BODY=$(jq -n --arg secret "${PDC_SECRET_KEY}" --arg service "${PDC_SERVICE_KEY}" \
            '{secretKey: $secret, serviceKey: $service}')
    echo -e "\n>>> Prepared request:"
    echo "${BODY}"

    RES=$(curl -sX POST "http://${PDC_NODE_IP}:${PDC_NODE_PORT}/login" \
        -H 'accept: application/json' -H 'Content-Type: application/json' \
        -d "${BODY}")

    echo
    if [[ $(jq '.code' <<<"${RES}") -ne 200 ]]; then
        echo -e "\n>>> Login request failed!"
        echo "${RES}" | jq
        exit 1
    else
        echo -e "\n>>> Login was successful!"
        echo "${RES}" > .pdc.login.json
    fi
    TOKEN=$(jq -r '.content.token' <<<"${RES}")
    echo -e "\nExtracted Bearer token: ${TOKEN}"
else
    echo -e "\n>>> Loading cached login response..."
    TOKEN=$(jq -r '.content.token' <.pdc.login.json)
    echo ">>> Validating Bearer token..."
    RET=$(curl -SsLv -o /dev/null -w '%{http_code}' "http:/${PDC_NODE_IP}:${PDC_NODE_PORT}/private/configuration/" \
                                                            -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}")
    if [[ "${RET}" -ne 200 ]]; then
        echo -e "\n>>> Invalid token! Removing cached response..."
        rm -f .pdc.login.json
        exit 0
    fi
fi

ENDPOINT="/private/configuration/"
echo
echo ">>> RUN ${ENDPOINT}"
curl -sX GET "http://${PDC_NODE_IP}:${PDC_NODE_PORT}${ENDPOINT}" \
    -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}" | jq

ENDPOINT="/private/catalogs/"
echo
echo ">>> RUN ${ENDPOINT}"
curl -sX GET "http://${PDC_NODE_IP}:${PDC_NODE_PORT}${ENDPOINT}" \
    -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}" | jq

ENDPOINT="/private/credentials/"
echo
echo ">>> RUN ${ENDPOINT}"
curl -sX GET "http://${PDC_NODE_IP}:${PDC_NODE_PORT}${ENDPOINT}" \
    -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}" | jq

ENDPOINT="/private/infrastructure/configurations/"
echo
echo ">>> RUN ${ENDPOINT}"
curl -sX GET "http://${PDC_NODE_IP}:${PDC_NODE_PORT}${ENDPOINT}" \
    -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}" | jq

ENDPOINT="/private/users/"
echo
echo ">>> RUN ${ENDPOINT}"
curl -sX GET "http://${PDC_NODE_IP}:${PDC_NODE_PORT}${ENDPOINT}" \
    -H 'accept: */*' -H "Authorization: Bearer ${TOKEN}" | jq