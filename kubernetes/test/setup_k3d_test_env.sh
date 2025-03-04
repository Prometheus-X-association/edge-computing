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

# Config --------------------------------------------------------------------------------

K3D_VER=v5.8.3
KUBECTL_VER=v1.31.5	# used by k3d v5.8.3 / k3s v1.31.5

NO_CHECK=false
SLIM_SETUP=false
UPDATE=false

CHECK_IMG="hello-world:latest"
TEST_K8S='test-cluster'
TEST_NS='ptx-edge'
TEST_ID='test42'
# busybox ~4.2MB
#TEST_IMG='busybox:latest'
#TEST_CMD='echo "Waiting to exit..." && time sleep infinity'
# pause ~240kB
TEST_IMG='k8s.gcr.io/pause'
TEST_CMD=''
TEST_OK='Running'

PZ_LAB='privacy-zone.dataspace.prometheus-x.org'
RET_VAL=0

# Parameters --------------------------------------------------------------------------------

function display_help() {
    cat <<EOF
Usage: $0 [options]

Options:
    -s  Only install minimum required binaries.
    -u  Update/overwrite dependencies.
    -x  Skip deployment validation.
    -h  Display help.
EOF
}

while getopts ":xsuh" flag; do
	case "${flag}" in
        x)
            echo "[x] No setup validation is configured."
            NO_CHECK=true;;
        s)
            echo "[x] Slim install is configured."
            SLIM_SETUP=true;;
        u)
            echo "[x] Update dependencies."
            UPDATE=true;;
        h)
            display_help
            exit
            ;;
        ?)
            echo "Invalid parameter: -${OPTARG} !"
            exit 1;;
    esac
done

# Install actions --------------------------------------------------------------------------------

function install_docker() {
	echo -e "\n>>> Install Docker[latest]...\n"
	sudo apt-get update && sudo apt-get install -y ca-certificates curl make
	curl -fsSL https://get.docker.com/ | sh
}

function install_k3d() {
	echo -e "\n>>> Install k3d binary[${K3D_VER}]...\n"
	sudo apt-get update && sudo apt-get install -y curl make
	curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | TAG=${K3D_VER} bash
}

function setup_k3d_bash_completion() {
    echo -e "\n>>> Install k3d bash completion...\n"
    sudo apt-get install -y bash-completion
    mkdir -p /etc/bash_completion.d
    k3d completion bash | sudo tee /etc/bash_completion.d/k3d > /dev/null
    sudo chmod a+r /etc/bash_completion.d/k3d
    source ~/.bashrc
}

function install_kubectl() {
	echo -e "\n>>> Install kubectl binary[${KUBECTL_VER}]...\n"
	curl -LO "https://dl.k8s.io/release/${KUBECTL_VER}/bin/linux/amd64/kubectl"
	sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
}

function setup_kubectl_bash_completion() {
    echo -e "\n>>> Install Kubectl bash completion...\n"
    sudo apt-get install -y bash-completion
    mkdir -p /etc/bash_completion.d
    kubectl completion bash | sudo tee /etc/bash_completion.d/kubectl > /dev/null
    sudo chmod a+r /etc/bash_completion.d/kubectl
    source ~/.bashrc
}

# Test actions --------------------------------------------------------------------------------

function setup_test_cluster() {
    echo -e "\n>>> Prepare test cluster with id: ${TEST_K8S}...\n"
#    k3d cluster create "$TEST_K8S" --wait --timeout=30s --servers=1 --agents=2 \
#        --k3s-node-label="$PZ_LAB/zone-C=true@server:0" \
#        --k3s-node-label="$PZ_LAB/zone-A=true@agent:0" \
#        --k3s-node-label="$PZ_LAB/zone-B=true@agent:*"
    cat <<EOF | k3d cluster create "${TEST_K8S}" --wait --timeout=30s --config=-
kind: Simple
apiVersion: k3d.io/v1alpha5
metadata:
  name: ${TEST_K8S}
servers: 1
agents: 2
options:
  k3d:
    wait: true
    timeout: "30s"
  k3s:
    nodeLabels:
      - label: "${PZ_LAB}/zone-C=true"
        nodeFilters:
          - server:0
      - label: "${PZ_LAB}/zone-A=true"
        nodeFilters:
          - agent:0
      - label: "${PZ_LAB/}zone-B=true"
        nodeFilters:
          - agent:*
EOF
    echo -e "\n>>> K3d cluster info:\n"
    kubectl cluster-info --context k3d-${TEST_K8S}
    echo -e "\n>>> K3s setup:\n"
    kubectl version
    echo
    kubectl -n kube-system get all
    echo -e "\n>>> K3s nodes:\n"
    kubectl get nodes -o wide -L ${PZ_LAB}/zone-A -L ${PZ_LAB}/zone-B -L ${PZ_LAB}/zone-C
}

function perform_test_deployment() {
    echo -e "\n>>> Perform a test deployment using ${TEST_IMG}...\n"
    # Validate K8s control plane
    set -x
    docker pull ${TEST_IMG}
    # k3d image import -c ${TEST_K8S} ${TEST_IMG}
    kubectl create namespace ${TEST_NS}
    kubectl -n ${TEST_NS} run ${TEST_ID} --image ${TEST_IMG} --restart='Never' \
                --overrides='{"apiVersion":"v1","spec":{"nodeSelector":{'\"${PZ_LAB}'/zone-A":"true"}}}' \
                -- /bin/sh -c "${TEST_CMD}"
    kubectl -n ${TEST_NS} wait --for="condition=Ready" --timeout=20s pod/${TEST_ID}
    set +x
    # Pod failure test
    echo -e "\n>>> Waiting for potential escalation...\n" && sleep 3s
    kubectl -n ${TEST_NS} get pod/${TEST_ID} -o wide
    echo
    if [[ "$(kubectl -n ${TEST_NS} get pod/${TEST_ID} -o jsonpath=\{.status.phase\})" == "${TEST_OK}" ]]; then
    	echo -e "\n>>> Validation result: OK!\n"
    else
    	echo -e "\n>>> Validation result: FAILED!\n"
    	RET_VAL=1
    fi
}

function cleanup_test_cluster() {
	echo -e "\n>>> Cleanup...\n"
	#kubectl delete pod ${TEST_ID} -n ${TEST_NS} --grace-period=0 #--force
	k3d cluster delete ${TEST_K8S}
	docker image ls -q -f "reference=ghcr.io/k3d-io/*" -f "reference=rancher/*" \
	                            -f "reference=${TEST_IMG}" | xargs -r docker rmi -f "${TEST_IMG}"
}

# Main --------------------------------------------------------------------------------

### Docker
if ! command -v docker >/dev/null 2>&1; then
    # Binaries
	install_docker
    # Privileged Docker
    sudo usermod -aG docker "${USER}"
    if [ ${NO_CHECK} = false ]; then
        echo -e "\n>>> Jump into new shell for docker group privilege...\n" && sleep 3s
        # New shell with docker group privilege
        exec sg docker "$0" "$@"
    fi
    # Validation
    if [ ${NO_CHECK} = false ]; then
        echo -e "\n>>> Check Docker install...\n"
        # Docker check with simple container
        docker run --rm "${CHECK_IMG}" && docker rmi -f "${CHECK_IMG}"
    fi
fi


### K3d
if ! command -v k3d >/dev/null 2>&1 || [ "${UPDATE}" = true ]; then
	# Binary
	install_k3d
    if [ ${SLIM_SETUP} = false ]; then
        # Bash completion
        setup_k3d_bash_completion
    fi
    # Validation
	echo
	(set -x; k3d version)
fi

### Kubectl
if ! command -v kubectl >/dev/null 2>&1 || [ "${UPDATE}" = true ]; then
	# Binary
	install_kubectl
    if [ ${SLIM_SETUP} = false ]; then
        # Bash completion
        setup_kubectl_bash_completion
    fi
    # Validation
	echo
	(set -x; kubectl version --client)
fi

# Register cleanup
trap cleanup_test_cluster ERR INT TERM #EXIT

# Test deployment
if [ ${NO_CHECK} = false ]; then
    # Setup cluster
    setup_test_cluster
    # Validation
    perform_test_deployment
    # Cleanup
    cleanup_test_cluster
fi

if [ ${NO_CHECK} = false ]; then
    cat <<EOF

#########################################################################################################
##  Shell session should be reloaded MANUALLY to make the non-root user access to Docker take effect!  ##
#########################################################################################################
EOF
    fi

echo -e "\nSetup is finished."
exit ${RET_VAL}
