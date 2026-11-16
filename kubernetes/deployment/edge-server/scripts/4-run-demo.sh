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

LOG "Run joint Edge Computing -- DVA demo..."

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
    _WKR="${1:?}"
    _INIT_COMPLETED="${2:-}"

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
    ${KCTL} logs -f --prefix --tail=-1 -l "app.kubernetes.io/name=${_WKR}" -c builder

    log "Waiting for worker: $(kubectl get pods -l app.kubernetes.io/name="${_WKR}" \
                                                        -o=jsonpath='{range .items[*]} | {.metadata.name}') to set up..."
    ${KCTL} wait --for="condition=Available" --timeout="${BUILD_TIMEOUT}s" "deployment/${_WKR}"
    if [ -n "${_INIT_COMPLETED}" ]; then
        (kubectl logs -f --prefix -c worker --tail=-1 --pod-running-timeout=20s -l "app.kubernetes.io/name=${_WKR}" &) \
                                                            | timeout "${BUILD_TIMEOUT}" grep -m1 "${_INIT_COMPLETED}"
    fi
    echo -e "\nWatching for <ready> state...."
    curl -SsL --fail-with-body -X GET "https://${CLUSTER_HOST}/${PREFIX}/workers/${_WKR}/watcher?state=ready&timeout=10" \
                                --cacert "${CA_DIR}/ca.crt" -u "${API_BASIC_USER}:${API_BASIC_PASSWORD}" \
                                -H 'Accept: application/json' | jq
    echo
    ${KCTL} get all,ingress -l "app.kubernetes.io/name=${_WKR}"
}

function deploy_dva_task(){
    _WKR="${1:?}"
    _INIT_COMPLETED="${2:-}"

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
    repeat_wait 5 ${KCTL} wait --for="condition=PodReadyToStartContainers" --timeout="${BUILD_TIMEOUT}s" pods \
                                                                            -l "app.kubernetes.io/name=${_WKR}"
    sleep 1
    ${KCTL} logs -f --prefix --tail=-1 -l "app.kubernetes.io/name=${_WKR}" -c builder

    log "Waiting for worker: $(kubectl get pods -l app.kubernetes.io/name="${_WKR}" \
                                                        -o=jsonpath='{range .items[*]} | {.metadata.name}') to set up..."
    sleep 1
    ${KCTL} wait --for="condition=Ready" --timeout="${BUILD_TIMEOUT}s" pods -l "app.kubernetes.io/name=${_WKR}"
    if [ -n "${_INIT_COMPLETED}" ]; then
        sleep 1
        (kubectl logs -f --prefix -c worker --tail=-1 --pod-running-timeout=20s -l "app.kubernetes.io/name=${_WKR}" &) \
                                                            | timeout "${BUILD_TIMEOUT}" grep -m1 "${_INIT_COMPLETED}"
    else
        sleep 10
    fi
    repeat_wait 5 ${KCTL} wait --for="condition=Complete" --timeout="5s" "job/${_WKR}"
    echo -e "\nWatching for <succeeded> state...."
    curl -SsL --fail-with-body -X GET "https://${CLUSTER_HOST}/${PREFIX}/workers/${_WKR}/watcher?state=succeeded&timeout=10" \
                                --cacert "${CA_DIR}/ca.crt" -u "${API_BASIC_USER}:${API_BASIC_PASSWORD}" \
                                -H 'Accept: application/json' | jq
    echo
    ${KCTL} get all,jobs,ingress -l "app.kubernetes.io/name=${_WKR}"
}

function wait_for_exposed() {
    _WKR="${1}"

    log "Waiting for ingress: $(kubectl get ingress -l app.kubernetes.io/name="${_WKR}" \
                                                    -o=jsonpath='{range .items[*]} | {.metadata.name}') to set up..."
    sleep 5
    ${KCTL} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout="${TIMEOUT}s" "ingress/${_WKR}"
    _URL="https://${CLUSTER_HOST}/worker/${_WKR}"
    log ">>> ${_WKR} is available on ${_URL}"
    wget -O /dev/null -Sq -nv --ca-certificate="${CA_DIR}/ca.crt" \
                                --user="${API_BASIC_USER}" --password="${API_BASIC_PASSWORD}" \
                                --retry-on-http-error=500,502 --waitretry=2 --read-timeout=3 --tries=10 "${_URL}"
    # curl -v -u "${API_BASIC_USER}:${API_BASIC_PASSWORD}" -L --location-trusted "http://${LB_DOMAIN}:${LB_WEB_PORT}/worker/${AGG}/"
    echo -e "\n>>> ${_WKR} is also exposed on https://${PRIMARY_HOST}/worker/${_WKR}"
    echo -e "\n>>> ${_WKR} is also exposed on https://${GW_HOST}/worker/${_WKR}"
}

########################################################################################################################

LOG "Deploying DVA components..."

deploy_dva_worker "postgres-provider" "PostgreSQL init process complete"
deploy_dva_worker "postgres-consumer" "PostgreSQL init process complete"
deploy_dva_worker "postgres-vlamanager" "PostgreSQL init process complete"
#
deploy_dva_worker "dva-processing-provider" "Application startup complete"
deploy_dva_worker "dva-processing-consumer" "Application startup complete"
deploy_dva_worker "dva-processing-vlamanager" "Application startup complete"
#
deploy_dva_worker "dva-vc-manager-provider" "Application startup complete"
deploy_dva_worker "dva-vc-manager-consumer" "Application startup complete"
deploy_dva_worker "vlamanager-backend" "Application startup complete"
deploy_dva_worker "vlamanager-frontend" "start worker processes" && wait_for_exposed "vlamanager-frontend"
#
deploy_dva_worker "dva-api-provider" "Application started"
deploy_dva_worker "dva-api-consumer" "Application started"
deploy_dva_worker "dva-dashboard-provider" "start worker processes" && wait_for_exposed "dva-dashboard-provider"
deploy_dva_worker "dva-dashboard-consumer" "start worker processes"
#
deploy_dva_worker "xapi-anonymizer" "Application startup complete"
deploy_dva_worker "xapi-aggregation" "Application startup complete"
#
deploy_dva_worker "edge-node-server-demo" "Application startup complete"
deploy_dva_task "karate" "HTML report"

########################################################################################################################

echo -e "\nDone."