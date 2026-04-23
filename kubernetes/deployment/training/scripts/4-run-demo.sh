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

log "Initiate Data Processing Function 0..."
envsubst <"rsc/worker-${DP0}-deployment.yaml" | ${KCTL} apply -f=-
${KCTL} wait --for="condition=PodReadyToStartContainers" --timeout="${BUILD_TIMEOUT}s" pods -l "app.kubernetes.io/name=${DP0}"
${KCTL} logs -f --prefix -l "app.kubernetes.io/name=${DP0}" -c builder

log "Waiting for worker to set up..."
${KCTL} wait --for="condition=Available" --timeout="${BUILD_TIMEOUT}s" "deployment/${DP0}"
(kubectl logs -f --prefix -c worker -l "app.kubernetes.io/name=${DP0}" &) | timeout "${TIMEOUT}" grep -m1 "Server started at"
echo
${KCTL} get all,ingress -l "app.kubernetes.io/name=${DP0}"

########################################################################################################################

log "Initiate Data Processing Function 1..."
envsubst <"rsc/worker-${DP1}-deployment.yaml" | ${KCTL} apply -f=-
${KCTL} wait --for="condition=PodReadyToStartContainers" --timeout="${BUILD_TIMEOUT}s" pods -l "app.kubernetes.io/name=${DP1}"
${KCTL} logs -f --prefix -l "app.kubernetes.io/name=${DP1}" -c builder

log "Waiting for worker to set up..."
${KCTL} wait --for="condition=Available" --timeout="${BUILD_TIMEOUT}s" "deployment/${DP1}"
(kubectl logs -f --prefix -c worker -l "app.kubernetes.io/name=${DP1}" &) | timeout "${TIMEOUT}" grep -m1 "Server started at"
echo
${KCTL} get all,ingress -l "app.kubernetes.io/name=${DP1}"

########################################################################################################################

log "Initiate Aggregator..."
envsubst <"rsc/worker-${AGG}-deployment.yaml" | ${KCTL} apply -f=-
${KCTL} wait --for="condition=PodReadyToStartContainers" --timeout="${BUILD_TIMEOUT}s" pods -l "app.kubernetes.io/name=${AGG}"
${KCTL} logs -f --prefix -l "app.kubernetes.io/name=${AGG}" -c builder

log "Waiting for worker to set up..."
${KCTL} wait --for="condition=Available" --timeout="${BUILD_TIMEOUT}s" "deployment/${AGG}"
(kubectl logs -f --prefix -c worker -l "app.kubernetes.io/name=${AGG}" &) | timeout "${TIMEOUT}" grep -m1 "Server started at"
echo
${KCTL} get all,ingress -l "app.kubernetes.io/name=${AGG}"

log "Waiting for ingress to set up[10s]..." && sleep 10
${KCTL} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout="${TIMEOUT}s" "ingress/${AGG}-mlflow-ui"
_AGG_URL="https://${CLUSTER_HOST}/worker/${AGG}/"
log ">>> Aggregator is available on ${_AGG_URL}"
wget --spider -S -nv --no-check-certificate --user="${API_BASIC_USER}" --password="${API_BASIC_PASSWORD}" "${_AGG_URL}"
log ">>> Aggregator is exposed on https://${PRIMARY_HOST}/worker/${AGG}/"
log ">>> Aggregator is exposed on https://${GW_HOST}/worker/${AGG}/"

########################################################################################################################

log "Initiate Orchestrator..."
envsubst <"rsc/worker-${ORCH}-deployment.yaml" | ${KCTL} apply -f=-
${KCTL} wait --for="condition=PodReadyToStartContainers" --timeout="${BUILD_TIMEOUT}s" pods -l "app.kubernetes.io/name=${ORCH}"
${KCTL} logs -f --prefix -l "app.kubernetes.io/name=${ORCH}" -c builder

log "Waiting for worker to set up..."
${KCTL} wait --for="condition=Available" --timeout="${BUILD_TIMEOUT}s" "deployment/${ORCH}"
(kubectl logs -f --prefix -c worker -l "app.kubernetes.io/name=${ORCH}" &) | timeout "${TIMEOUT}" grep -m1 "Server started at"
echo
${KCTL} get all,ingress -l "app.kubernetes.io/name=${ORCH}"

log "Waiting for ingress to set up[10s]..." && sleep 10
${KCTL} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout="${TIMEOUT}s" "ingress/${ORCH}"
_ORCH_URL="https://${CLUSTER_HOST}/worker/${ORCH}/docs"
log ">>> Orchestrator is available on ${_ORCH_URL}"
wget --spider -S -nv --no-check-certificate --user="${API_BASIC_USER}" --password="${API_BASIC_PASSWORD}" "${_ORCH_URL}"
log ">>> Orchestrator is exposed on https://${PRIMARY_HOST}/worker/${ORCH}/docs"
log ">>> Orchestrator is exposed on https://${GW_HOST}/worker/${ORCH}/docs"

########################################################################################################################
echo -e "\nDone."