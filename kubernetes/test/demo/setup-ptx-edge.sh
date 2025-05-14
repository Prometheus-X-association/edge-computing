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

LOG "Setting up PTX-edge components..."

log "Deploy REST-API"
kubectl create namespace "${PTX}"
#kubectl -n "${PTX}" create deployment "${REST_API}" --image "${API_IMG}" --replicas=1 --port="${API_PORT}"
# shellcheck disable=SC2016
envsubst <"rsc/restapi-deployment.yaml" | kubectl apply -f=-
kubectl -n "${PTX}" wait --for="condition=Available" --timeout="${TIMEOUT}s" "deployment/${REST_API}"
kubectl -n "${PTX}" expose "deployment/${REST_API}" --target-port="${API_PORT}" --port="${API_PORT}" --name="${REST_API}"
echo
kubectl -n "${PTX}" get pods,endpointslices

log "Configure ingress"
kubectl -n "${PTX}" create ingress "${REST_API}" --rule="/${PREFIX}/*=${REST_API}:${API_PORT},tls" --class=traefik \
                    --default-backend="${REST_API}:${API_PORT}" --annotation="ingress.kubernetes.io/ssl-redirect=false"
kubectl -n "${PTX}" wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout="${TIMEOUT}s" "ingress/${REST_API}"
echo
kubectl -n "${PTX}" get ingress

log "Waiting for ingress to set up..." && sleep 10
INGRESS_IP="$(kubectl -n "${PTX}" get "ingress/${REST_API}" -o jsonpath='{.status.loadBalancer.ingress[].ip}')"
echo ">>> ${REST_API} is exposed on  http://${INGRESS_IP}:80/${PREFIX}/ui/"
echo ">>> ${REST_API} is exposed on https://${INGRESS_IP}:443/${PREFIX}/ui/"
echo ">>> ${REST_API} is exposed on  http://localhost:8080/${PREFIX}/ui/"
curl -I "http://localhost:8080/${PREFIX}/ui/"

log "Set up PTX-core sandbox"
docker compose -f ../ptx/core/docker-compose.yaml up -d --force-recreate --wait --wait-timeout="${TIMEOUT}"

log "Deploy per-zone PDCs"
# Replace only the given envvars parameters with the given format ${}
envsubst <"rsc/pdc-config.yaml" '${PTX} ${PDC} ${PDC_PORT} ${PDC_NODE_PORT} ${PDC_PREFIX}' | kubectl apply -f=-
envsubst <"rsc/pdc-daemonset.yaml" | kubectl apply -f=-
kubectl -n "${PTX}" wait --for=jsonpath='.status.numberReady'=2 "daemonset/${PDC}"
echo
kubectl -n "${PTX}" get daemonsets,configmaps,secrets

log "Waiting for PDC instances to set up..."
for pod in $(kubectl -n "${PTX}" get pods -l app="${PDC}" -o jsonpath='{.items[*].metadata.name}'); do
    ( kubectl -n "${PTX}" logs -f "pods/${pod}" -c ptx-connector & ) | timeout "${TIMEOUT}" grep -m1 "Server running on"
done
for node in $(kubectl -n "${PTX}" get pods -l app="${PDC}" -o jsonpath='{.items[*].status.hostIP}'); do
    echo -e "\n>>> PDC instance is exposed on http://${node}:${PDC_NODE_PORT}/"
    curl -Ssf -I "http://${node}:${PDC_NODE_PORT}/"
done

########################################################################################################################

echo -e "\nDone."