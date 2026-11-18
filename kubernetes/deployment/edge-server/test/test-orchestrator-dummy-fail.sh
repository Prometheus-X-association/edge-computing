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

LOG "Run orchestrator-managed DVA attestation test with dummy datasets"

anonVLAID=${1:?'Missing exported envvar: anonVLAID as param[1]!'}
aggVLAID=${2:?'Missing exported envvar: aggVLAID! as param[2]!'}

DUMMY_DATA="${SCRIPT_DIR}/test/dummy_records_fail.json"

########################################################################################################################

log "Create request originated from PDC..."

echo -e "\nUsed anonymizedVlaID: ${anonVLAID}"
echo -e "\nUsed aggregatedVlaID: ${aggVLAID}"
echo -e "\nUsed dummy data: ${DUMMY_DATA}"

EXCHANGE_BODY=$(jq -n --arg anon "$anonVLAID" \
                        --arg agg "$aggVLAID" \
                        --arg contract "${PTX_CONTRACT_URI}contract/${SC_CONTRACT_ID}" \
                        --slurpfile data "${DUMMY_DATA}" \
                        '{
                          params: {
                              anonymizedVlaID: $anon,
                              aggregatedVlaID: $agg
                          },
                          contract: $contract,
                          data: $data[0]
                        }')

echo -e "\nPrepared request body:"
echo "${EXCHANGE_BODY}" | jq

log "Invoking orchestrator..."

_URL="https://${LB_DOMAIN}:${LB_WEBSECURE_PORT}/worker/edge-node-server-demo/analyse"
echo -e "\nUsed URL: [POST] ${_URL}"

RESP=$(time curl -Ss -k --fail-with-body -X POST \
                                            "${_URL}" \
                                            -H "Content-Type: application/json" \
                                            -H "Accept: application/json" \
                                            -H "x-ptx-dataExchangeId: 3f9b6c1e-7a42-4d58-9c0e-2b1a8d5e6f47" \
                                            -H "x-ptx-contractId: ${SC_CONTRACT_ID}" \
                                            -d "${EXCHANGE_BODY}")

echo -e "\nReceived response:"
echo "${RESP}" | jq

if [ "$(jq '.attestations.anonymized.evaluationResults[0].success' <<<"${RESP}")" != "true" ] || \
   [ "$(jq '.attestations.aggregated.evaluationResults[0].success' <<<"${RESP}")" != "true" ]; then
    error "Data attestations failed!" && exit 1
else
    LOG "Data attestations was successful!"
fi

########################################################################################################################

echo -e "\nDone."