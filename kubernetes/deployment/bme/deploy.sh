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

source ./bme-setup-config.sh

########################################################################################################################

function cleanup() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    k3d cluster list "${CLUSTER}" || cluster_missing="$?"
    if [ ! "${cluster_missing-0}" ]; then
        kubectl delete namespace "${NAMESPACE}" --ignore-not-found --now || true
    fi
    k3d cluster delete "${CLUSTER}" || true
    rm -rf "${CFG_DIR}/.cache"
    docker image ls -qf "reference=ptx/*" -f "reference=ptx-edge/*" | xargs -r docker rmi -f
	docker image prune -f
}

function build() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    for modul in ${PTX_EDGE_COMPONENTS}; do
        make -C "${PROJECT_ROOT}/src/${modul}" build
    done
	make -C "${PROJECT_ROOT}/src/ptx" build-pdc
    echo
    echo ">>> Created images:"
	docker image ls -f "reference=ptx/*" -f "reference=ptx-edge/*"
	echo
}

function setup() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
    k3d cluster create --config="${CFG_DIR}/k3d-bme-cluster.yaml"
	kubectl create namespace "${NAMESPACE}" && kubectl config set-context --current --namespace "${NAMESPACE}"
	for img in ${PTX_EDGE_COMPONENTS}; do
        IMG=$(docker image ls -f reference="ptx-edge/${img}*" --format='{{.Repository}}:{{.Tag}}')
        skopeo copy --dest-cert-dir="${CA_DIR}" --dest-creds="${CREDS}" "docker-daemon:${IMG}" "docker://${K3D_REG}/${IMG}"
    done
    for img in ${PDC_COMPONENTS}; do
		IMG=$(docker image ls -f reference="ptx/${img}*" --format='{{.Repository}}:{{.Tag}}')
		skopeo copy --dest-cert-dir="${CA_DIR}" --dest-creds="${CREDS}" "docker-daemon:${IMG}" "docker://${K3D_REG}/${IMG}"
	done
    echo
	echo ">>> Uploaded images:"
	curl -Sskf --cacert "${CA_DIR}/ca.crt" -u "${CREDS}" -X GET "https://${K3D_REG}/v2/_catalog" | python3 -m json.tool
	echo
}

function deploy() {
    echo
    echo ">>>>>>>>> Invoke ${FUNCNAME[0]}....."
    echo
	envsubst <"${CFG_DIR}/ptx-pdc-daemon.yaml" | kubectl apply -f=-
	kubectl wait --for=jsonpath='.status.numberReady'=1 --timeout="${TIMEOUT}" daemonset/pdc
	echo "Waiting for PDC to set up..."
	for pod in $(kubectl get pods -l app=pdc -o jsonpath='{.items[*].metadata.name}'); do
		( kubectl logs -f pod/"${pod}" -c ptx-connector & ) | timeout "${TIMEOUT}" grep -m1 "Server running on"
	done
}

function status() {
    echo
    echo ">>>>>>>>> Cluster[${CLUSTER}] deployment status:"
    echo
	kubectl get all,endpointslices,configmaps,secrets,ingress -o wide
}

########################################################################################################################

echo
echo "Start deployment of cluster: ${CLUSTER}"
echo

########################################################################################################################

function display_help() {
    cat <<EOF
Usage: $0 [options]

Options:
    -c  Only perform cleanup.
    -t  Set global timeout parameter (def: ${TIMEOUT})
    -h  Display help.
EOF
}

while getopts ":t:ch" flag; do
	case "${flag}" in
        c)
            cleanup
            exit 0
            ;;
        t)
            TIMEOUT=${OPTARG}
            echo "Global timeout set to ${TIMEOUT}"
            ;;
        h)
            display_help
            exit 2
            ;;
        ?)
            echo "Invalid parameter: -${OPTARG} !"
            exit 1
            ;;
    esac
done

########################################################################################################################

cleanup
build
setup
deploy
status

########################################################################################################################

echo
echo "Cluster: ${CLUSTER} deployed."
echo