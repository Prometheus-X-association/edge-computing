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

LOG "Setting up PTX-core sandbox..."
${KCTL} create namespace "${SANDBOX}"
envsubst <"${SCRIPT_DIR}/rsc/ptx-sandbox-catalog.yaml" | ${KCTL} -n "${SANDBOX}" apply -f=-
${KCTL} -n "${SANDBOX}" wait --for="condition=Ready" --timeout="${TIMEOUT}s" "pod/${CATALOG}"
echo
${KCTL} -n "${SANDBOX}" get all -o wide -l "app.kubernetes.io/name=${CATALOG}"

log ">>> PTX-core catalog is reachable on ${CATALOG_DNS}"
${KCTL} -n "${SANDBOX}" run --rm --restart=Never --image busybox:latest -ti "check" --command -- \
                        sh -c "nslookup ${CATALOG_DNS}; wget -T3 -qO- http://${CATALOG_DNS}:3002/__admin/health; echo"

########################################################################################################################

LOG "Setting up PTX-edge components..."
${KCTL} create namespace "${PTX}"
${KCTL} config set-context --current --namespace "${PTX}"

########################################################################################################################

log "Setup registry configuration..."
${KCTL} create configmap registry-root-ca.crt --from-file="ca.crt=${ROOT_DIR}/src/registry/.certs/ca/ca.crt"

########################################################################################################################

log "Setup PDC configuration..."
envsubst <"${SCRIPT_DIR}/rsc/pdc-daemon-config.yaml" | ${KCTL} apply -f=-
echo
${KCTL} get configmaps,secrets,serviceaccount,role,rolebinding,clusterrole,clusterrolebinding -l "app.kubernetes.io/name=${PDC}"

log "Deploy per-zone PDCs"
envsubst <"${SCRIPT_DIR}/rsc/pdc-daemon-cluster.yaml" | ${KCTL} apply -f=-
${KCTL} wait --for=jsonpath='.status.numberReady'=2 --timeout="${TIMEOUT}s" "daemonset/${PDC}"
echo
${KCTL} get all,daemonset,ingress,middleware.traefik.io -l "app.kubernetes.io/name=${PDC}"

log "Waiting for PDC instances to set up..."
for pod in $(kubectl get pods -l "app.kubernetes.io/name=${PDC}" -o jsonpath='{.items[*].metadata.name}'); do
    ( kubectl logs -f "pods/${pod}" -c connector --prefix & ) | timeout "${TIMEOUT}" grep -m1 "Server running on"
done
for node in $(kubectl get pods -l "app.kubernetes.io/name=${PDC}" -o jsonpath='{.items[*].status.hostIP}'); do
    echo -e "\n>>> PDC instance is exposed on http://${node}:${PDC_NODE_PORT}/"
    curl -Ssf -I "http://${node}:${PDC_NODE_PORT}/"
done

log "Waiting for ingress to set up..." && sleep 10
${KCTL} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout="${TIMEOUT}s" "ingress/${PDC}-${PZ_A}"
${KCTL} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout="${TIMEOUT}s" "ingress/${PDC}-${PZ_B}"

log ">>> PDC is exposed on http://${LB_HOST}/${PDC_PREFIX_A}"
curl -I "http://${LB_HOST}/${PDC_PREFIX_A}"
curl -Ssf "http://${LB_HOST}/${PDC_PREFIX_A}" | grep "href" | head -n1

log ">>> PDC is exposed on http://${LB_HOST}/${PDC_PREFIX_B}"
curl -I "http://${LB_HOST}/${PDC_PREFIX_B}"
curl -Ssf "http://${LB_HOST}/${PDC_PREFIX_B}" | grep "href" | head -n1

########################################################################################################################

log "Deploy REST-API"
envsubst <"${SCRIPT_DIR}/rsc/restapi-deployment.yaml" | ${KCTL} apply -f=-
${KCTL} wait --for="condition=Available" --timeout="${TIMEOUT}s" "deployment/${REST_API}"
echo
${KCTL} get all,ingress -l "app.kubernetes.io/name=${REST_API}"

log "Waiting for ingress to set up..." && sleep 10
${KCTL} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout="${TIMEOUT}s" "ingress/${REST_API}"

log ">>> ${REST_API} is exposed on http://${LB_HOST}/${PREFIX}/ui/"
curl -I "http://${LB_HOST}/${PREFIX}/ui/"
curl -LSs "http://${LB_HOST}/${PREFIX}/versions" | python3 -m json.tool

########################################################################################################################

log "Deploy scheduler"
envsubst <"${SCRIPT_DIR}/rsc/scheduler-deployment.yaml" | ${KCTL} apply -f=-
${KCTL} wait --for="condition=Available" --timeout="${TIMEOUT}s" "deployment/${SCHEDULER}"
echo
${KCTL} get all,daemonset,ingress,middleware.traefik.io -l "app.kubernetes.io/name=${SCHEDULER}"

########################################################################################################################

echo -e "\nDone."