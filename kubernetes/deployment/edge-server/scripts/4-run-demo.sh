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

LOG "Run joint Edge Computing -- AI Training (BB-01/02) demo..."

########################################################################################################################

if [ "${LOCAL_SETUP}" = "true" ]; then
    warning "Setup is configured for local datasource!"
fi

_REST_API_URL="https://${CLUSTER_HOST}/${PREFIX}"
log ">>> Validating rest-api availability on ${_REST_API_URL}/health"
curl -fSsL --location-trusted --cacert "${CA_DIR}/ca.crt" -u "${API_BASIC_USER}:${API_BASIC_PASSWORD}" -o /dev/null \
                                                                            "https://${CLUSTER_HOST}/${PREFIX}/health"
echo -e "Validation successful!\n"

function deploy_dva_worker(){
    _WKR="${1}"
    _INIT_COMPLETED="${2}"

    log "Initiate ${_WKR}..."
    _WRK_REQ_BODY=$(envsubst <"${SCRIPT_DIR}/request/${_WKR}.json")
    echo "Prepared body:" && echo "${_WRK_REQ_BODY}" | jq -r .
    echo -e "\nReceived response:"
    curl -SsL --fail-with-body -X PUT "https://${CLUSTER_HOST}/${PREFIX}/workers/${_WKR}" \
                                --cacert "${CA_DIR}/ca.crt" -u "${API_BASIC_USER}:${API_BASIC_PASSWORD}" \
                                -H "Content-Type: application/json" \
                                -H 'Accept: application/json' \
                                --data-binary @<(echo "${_WRK_REQ_BODY}" | jq -c .) | jq

    log "Wait for ${_WKR}..."
    repeat_wait 5 ${KCTL} wait --for="condition=Processed" "ptxedgeworker/${_WKR}"
    repeat_wait 5 ${KCTL} wait --for="condition=Progressing" --timeout="5s" "deployment/${_WKR}"
    repeat_wait 5 ${KCTL} wait --for="condition=PodReadyToStartContainers" --timeout="${BUILD_TIMEOUT}s" pods \
                                                                            -l "app.kubernetes.io/name=${_WKR}"
    sleep 1
    ${KCTL} logs -f --prefix -l "app.kubernetes.io/name=${_WKR}" -c builder

    log "Waiting for worker: $(kubectl get pods -l app.kubernetes.io/name="${_WKR}" \
                                                        -o=jsonpath='{range .items[*]} | {.metadata.name}') to set up..."
    ${KCTL} wait --for="condition=Available" --timeout="${BUILD_TIMEOUT}s" "deployment/${_WKR}"
    (kubectl logs -f --prefix -c worker -l "app.kubernetes.io/name=${_WKR}" &) \
                                                        | timeout "${TIMEOUT}" grep -m1 "${_INIT_COMPLETED}"
    echo -e "\nWatching for <ready> state...."
    curl -SsL --fail-with-body -X GET "https://${CLUSTER_HOST}/${PREFIX}/workers/${_WKR}/watcher?state=ready&timeout=10" \
                                --cacert "${CA_DIR}/ca.crt" -u "${API_BASIC_USER}:${API_BASIC_PASSWORD}" \
                                -H 'Accept: application/json' | jq
    echo
    ${KCTL} get all,ingress -l "app.kubernetes.io/name=${_WKR}"
}

########################################################################################################################

deploy_dva_worker "postgres-provider" "PostgreSQL init process complete"
deploy_dva_worker "postgres-consumer" "PostgreSQL init process complete"
deploy_dva_worker "postgres-vlamanager" "PostgreSQL init process complete"

deploy_dva_worker "dva-processing-consumer" "Application startup complete"
deploy_dva_worker "dva-processing-provider" "Application startup complete"
deploy_dva_worker "dva-processing-vlamanager" "Application startup complete"

########################################################################################################################


#log "Waiting for ingress:$(kubectl get ingress -l app.kubernetes.io/name="${AGG}" \
#                                                    -o=jsonpath='{range .items[*]} | {.metadata.name}') to set up..."
#sleep 5
#${KCTL} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout="${TIMEOUT}s" "ingress/${AGG}"
#_AGG_URL="https://${CLUSTER_HOST}/worker/${AGG}/"
#log ">>> Aggregator is available on ${_AGG_URL}"
#wget -O /dev/null -Sq -nv --ca-certificate="${CA_DIR}/ca.crt" \
#                            --user="${API_BASIC_USER}" --password="${API_BASIC_PASSWORD}" \
#                            --retry-on-http-error=500,502 --waitretry=2 --read-timeout=3 --tries=10 "${_AGG_URL}"
## curl -v -u "${API_BASIC_USER}:${API_BASIC_PASSWORD}" -L --location-trusted "http://${LB_DOMAIN}:${LB_WEB_PORT}/worker/${AGG}/"
#log ">>> Aggregator is also exposed on https://${PRIMARY_HOST}/worker/${AGG}\n
#>>> Aggregator is also exposed on https://${GW_HOST}/worker/${AGG}/"

########################################################################################################################

echo -e "\nDone."