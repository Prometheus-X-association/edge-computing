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
source config.sh

########################################################################################################################

LOG "Execute Edge Computing (BB-02) demo..."

log "Initiate Data Processing Function without dataspace restriction"
envsubst <"rsc/${TASK1}-job.yaml" | ${KCTL} apply -f=-
${KCTL} wait --for='jsonpath={.status.phase}=Bound' --timeout="${TIMEOUT}s" "pvc/${TASK1}-pvc"
echo
${KCTL} get pv,pvc,jobs -o wide -l "app.kubernetes.io/name=${TASK1}"
echo
${KCTL} wait --for="condition=PodReadyToStartContainers" --timeout="${TIMEOUT}s" pods -l "app.kubernetes.io/name=${TASK1}"
${KCTL} logs -f --prefix "job/${TASK1}" builder
${KCTL} wait --for="condition=ContainersReady" --timeout="${TIMEOUT}s" pods -l "app.kubernetes.io/name=${TASK1}"
${KCTL} logs -f --prefix "job/${TASK1}" worker

${KCTL} wait --for="condition=Complete" --timeout="${TIMEOUT}s" "job/${TASK1}"
wait_enter "with Privacy Preserving"

########################################################################################################################

log "Initiate Data Processing Function with Privacy Zone restriction"
envsubst <"rsc/${TASK2}-job.yaml" | ${KCTL} apply -f=-
${KCTL} wait --for='jsonpath={.status.phase}=Bound' --timeout="${TIMEOUT}s" "pvc/${TASK2}-pvc"
echo
${KCTL} get pv,pvc,jobs -o wide -l "app.kubernetes.io/name=${TASK2}"
echo
${KCTL} wait --for="condition=PodReadyToStartContainers" --timeout="${TIMEOUT}s" pods -l "app.kubernetes.io/name=${TASK2}"
${KCTL} logs -f --prefix "job/${TASK2}" builder
${KCTL} wait --for="condition=ContainersReady" --timeout="${TIMEOUT}s" pods -l "app.kubernetes.io/name=${TASK2}"
${KCTL} logs -f --prefix "job/${TASK2}" worker

${KCTL} wait --for="condition=Complete" --timeout="${TIMEOUT}s" "job/${TASK2}"
wait_enter "with Near-Data Processing"

########################################################################################################################

log "Initiate Data Processing Function with efficient near-data processing"
envsubst <"rsc/${TASK3}-job.yaml" | ${KCTL} apply -f=-
${KCTL} wait --for='jsonpath={.status.phase}=Bound' --timeout="${TIMEOUT}s" "pvc/${TASK3}-pvc"
echo
${KCTL} get pv,pvc,jobs -o wide -l "app.kubernetes.io/name=${TASK3}"
echo
${KCTL} wait --for="condition=PodReadyToStartContainers" --timeout="${TIMEOUT}s" pods -l "app.kubernetes.io/name=${TASK3}"
${KCTL} logs -f --prefix "job/${TASK3}" builder
${KCTL} wait --for="condition=ContainersReady" --timeout="${TIMEOUT}s" pods -l "app.kubernetes.io/name=${TASK3}"
${KCTL} logs -f --prefix "job/${TASK3}" worker

${KCTL} wait --for="condition=Complete" --timeout="${TIMEOUT}s" "job/${TASK3}"

########################################################################################################################

echo -e "\nDone."