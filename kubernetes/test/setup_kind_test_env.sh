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

KIND_VER=v0.26.0
#KUBECTL_VER=$(curl -L -s https://dl.k8s.io/release/stable.txt)
KUBECTL_VER=v1.32.2	# used by Kind v0.27.0
KIND_CCM_VER=0.6.0

ROOTLESS=false
NO_CHECK=false
SLIM_SETUP=false
KIND_CCM=false
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
KIND_CCM_NAME="kind-ccm"

PZ_LAB='privacy-zone.dataspace.prometheus-x.org'
RET_VAL=0

# Parameters --------------------------------------------------------------------------------

function display_help() {
    cat <<EOF
Usage: $0 [options]

Options:
    -c  Install Kind's cloud provider manager.
    -r  Install Docker and Kind in rootless mode.
    -s  Only install minimum required binaries.
    -u  Update/overwrite dependencies.
    -x  Skip deployment validation.
    -h  Display help.
EOF
}

while getopts ":rxscuh" flag; do
	case "${flag}" in
		r)
			ROOTLESS=true
			cat <<EOF

[x] Rootless setup is configured.

It may cause performance degradation of misbehavior due to different restrictions!
See more:
	- https://docs.docker.com/engine/security/rootless/#known-limitations
	- https://kind.sigs.k8s.io/docs/user/rootless/#restrictions

EOF
            sleep 3s;;
        x)
            echo "[x] No setup validation is configured."
            NO_CHECK=true;;
        s)
            echo "[x] Slim install is configured."
            SLIM_SETUP=true;;
        c)
            echo "[x] Cloud provider kind install is configured."
            KIND_CCM=true;;
        u)
            echo "[x] Update dependencies."
            UPDATE=true;;
        h)
            display_help
            exit;;
        ?)
            echo "Invalid parameter: -${OPTARG} !"
            exit 1;;
    esac
done

# Install actions --------------------------------------------------------------------------------

function install_docker() {
	echo -e "\n>>> Install Docker[latest]...\n"
	sudo apt-get update && sudo apt-get install -y ca-certificates curl
	curl -fsSL https://get.docker.com/ | sh
}

function setup_rootless_docker() {
	echo -e "\n>>> Setup rootless Docker...\n"
    sudo apt-get update && sudo apt-get install -y uidmap
    dockerd-rootless-setuptool.sh install
    sudo loginctl enable-linger "${USER}"
    echo -e "\n# Rootless docker\nexport DOCKER_HOST=unix:///run/user/1000/docker.sock" >> ~/.bashrc
    source ~/.bashrc
    # Add support for Ubuntu 24.04
    source /etc/lsb-release
    if [ "$DISTRIB_RELEASE" = 24.04 ]; then
        filename=$(echo "${HOME}"/bin/rootlesskit | sed -e s@^/@@ -e s@/@.@g)
        cat <<EOF > ~/"$filename"
abi <abi/4.0>,
include <tunables/global>

"${HOME}/bin/rootlesskit" flags=(unconfined) {
  userns,

  include if exists <local/${filename}>
}
EOF
        sudo mv ~/"$filename" /etc/apparmor.d/"$filename"
        sudo systemctl restart apparmor.service
    fi
}

function install_kind() {
	echo -e "\n>>> Install Kind binary[${KIND_VER}]...\n"
	sudo apt-get update && sudo apt-get install -y curl make git
	[ "$(uname -m)" = x86_64 ] && curl -Lo ./kind "https://kind.sigs.k8s.io/dl/${KIND_VER}/kind-linux-amd64"
	chmod +x ./kind
	sudo mv -v ./kind /usr/local/bin/kind
}

function install_cloud_provider_kind() {
	echo -e "\n>>> Install Cloud Provider Kind[v${KIND_CCM_VER}]...\n"
    # docker pull registry.k8s.io/cloud-provider-kind/cloud-controller-manager:v${KIND_CCM_VER}
    pushd "$(mktemp -d)"
    wget -qO- "https://github.com/kubernetes-sigs/cloud-provider-kind/releases/download/v${KIND_CCM_VER}/cloud-provider-kind_${KIND_CCM_VER}_linux_amd64.tar.gz" | tar xvz
    sudo mv cloud-provider-kind /usr/local/bin/cloud-provider-kind
    popd
}

function setup_kind_bash_completion() {
    echo -e "\n>>> Install Kind bash completion...\n"
    sudo apt-get install -y bash-completion
    mkdir -p /etc/bash_completion.d
    kind completion bash | sudo tee /etc/bash_completion.d/kind > /dev/null
    sudo chmod a+r /etc/bash_completion.d/kind
    source ~/.bashrc
}

function setup_rootless_kind() {
    echo -e "\n>>> Install rootless Kind...\n"
    sudo su -c "mkdir -p /etc/systemd/system/user@.service.d/ &&
        echo -e '[Service]\nDelegate=yes' > /etc/systemd/system/user@.service.d/delegate.conf"
    sudo su -c "mkdir -p /etc/modules-load.d/ &&
        echo -e 'ip6_tables\nip6table_nat\nip_tables\niptable_nat' > /etc/modules-load.d/iptables.conf"
    sudo systemctl daemon-reload
    sudo sysctl -w kernel.dmesg_restrict=0
    systemctl --user restart docker
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
    # kind create cluster -n "$TEST_K8S" --wait=30s --config=manifests/kind_test_cluster_multi.yaml
    cat <<EOF | kind create cluster -n "${TEST_K8S}" --wait=30s --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ${TEST_K8S}
nodes:
  - role: control-plane
    labels:
      ${PZ_LAB}/zone-C: true
  - role: worker
    labels:
      ${PZ_LAB}/zone-A: true
      ${PZ_LAB}/zone-B: true
  - role: worker
    labels:
      ${PZ_LAB}/zone-B: true
EOF
    echo -e "\n>>> Kind cluster info:\n"
    kubectl cluster-info --context kind-${TEST_K8S}
    echo -e "\n>>> K8s setup:\n"
    kubectl version
    echo
    kubectl -n kube-system get all
    echo -e "\n>>> K8s nodes:\n"
    kubectl get nodes -o wide -L ${PZ_LAB}/zone-A -L ${PZ_LAB}/zone-B -L ${PZ_LAB}/zone-C
}

function setup_kind_ccm() {
    echo -e "\n>>> Initiate Kind's Cloud Controller Manager(CCM)[v${KIND_CCM_VER}]...\n"
    docker run -q --rm -d --name ${KIND_CCM_NAME} --network kind -v /var/run/docker.sock:/var/run/docker.sock \
										"registry.k8s.io/cloud-provider-kind/cloud-controller-manager:v${KIND_CCM_VER}"
	docker ps
}

function perform_test_deployment() {
    echo -e "\n>>> Perform a test deployment using ${TEST_IMG}...\n"
    # Validate K8s control plane
    set -x
    docker pull ${TEST_IMG}
    # kind load docker-image -n ${TEST_K8S} ${TEST_IMG}
    kubectl create namespace ${TEST_NS}
    kubectl -n ${TEST_NS} run ${TEST_ID} --image ${TEST_IMG} --restart='Never' \
                --overrides='{"apiVersion":"v1","spec":{"nodeSelector":{'\"${PZ_LAB}'/zone-A":"true"}}}' \
                -- /bin/sh -c "${TEST_CMD}"
    kubectl -n ${TEST_NS} wait --for=condition=Ready --timeout=20s pod/${TEST_ID}
    set +x
    # Pod failure test
    echo -e "\n>>> Waiting for potential escalation...\n" && sleep 3s
    kubectl -n ${TEST_NS} get pods ${TEST_ID} -o wide
    echo
    if [[ "$(kubectl -n ${TEST_NS} get pods/${TEST_ID} -o jsonpath=\{.status.phase\})" == "${TEST_OK}" ]]; then
    	echo -e "\n>>> Validation result: OK!\n"
    else
    	echo -e "\n>>> Validation result: FAILED!\n"
    	kind export logs "./${TEST_ID}-failed" -n ${TEST_NS} --verbosity=2
    	RET_VAL=1
    fi
}

function perform_lb_deployment() {
    echo -e "\n>>> Perform a LoadBalancer test deployment for ${TEST_ID}...\n"
    kubectl -n ${TEST_NS} expose pod/${TEST_ID} --name=${TEST_ID} --type=LoadBalancer --target-port=8888 --port=8888
    kubectl -n ${TEST_NS} wait --for=jsonpath='{.status.loadBalancer.ingress}' --timeout=20s service/${TEST_ID}
    kubectl -n ${TEST_NS} get services,endpoints -o wide
    if [[ "$(kubectl -n ${TEST_NS} get services/${TEST_ID} -o jsonpath=\{.status.loadBalancer.ingress[].ip\})" ]]; then
        echo -e "\n>>> Validation result: OK!\n"
    else
        echo -e "\n>>> Validation result: FAILED!\n"
        kind export logs "./${TEST_ID}-failed" -n ${TEST_NS} --verbosity=2
        RET_VAL=1
    fi
}

function cleanup_test_cluster() {
	echo -e "\n>>> Cleanup...\n"
	#kubectl delete pod ${TEST_ID} -n ${TEST_NS} --grace-period=0 #--force
	kind delete cluster -n ${TEST_K8S}
	docker ps -q -f "name=${KIND_CCM_NAME}" -f "name=${TEST_K8S}*" -f "name=kindccm-*" | xargs -r docker kill
    #docker container prune -f
    docker images -q -f "reference=registry.k8s.io/cloud-provider-kind/*" -f "reference=envoyproxy/*" \
                    -f "reference=${TEST_IMG}" -f "reference=kindest/*" | xargs -r docker rmi -f
    #docker image prune -f
}

# Main --------------------------------------------------------------------------------

### Docker
if ! command -v docker >/dev/null 2>&1; then
    # Binaries
	install_docker
	if [ ${ROOTLESS} = true ]; then
	    # Rootless Docker
		setup_rootless_docker
	else
		# Privileged Docker
		sudo usermod -aG docker "$USER"
		if [ ${NO_CHECK} = false ]; then
            echo -e "\n>>> Jump into new shell for docker group privilege...\n" && sleep 3s
            # New shell with docker group privilege
            exec sg docker "$0" "$@"
        fi
	fi
	# Validation
    if [ ${NO_CHECK} = false ]; then
        echo -e "\n>>> Check Docker install...\n"
        # Docker check with simple container
        docker run --rm "${CHECK_IMG}" && docker rmi -f "${CHECK_IMG}"
    fi
fi


### Kind
if ! command -v kind >/dev/null 2>&1 || [ "${UPDATE}" = true ]; then
	# Binary
	install_kind
    if [ ${SLIM_SETUP} = false ]; then
        # Bash completion
        setup_kind_bash_completion
    fi
	# Rootless Kind
	if [ ${ROOTLESS} = true ]; then
	    setup_rootless_kind
	fi
    # Validation
	echo
	(set -x; kind version)
fi

### Cloud provider Kind
if [ ${KIND_CCM} = true ] && { ! command -v cloud-provider-kind >/dev/null 2>&1 || [ "${UPDATE}" = true ]; }; then
    install_cloud_provider_kind
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
trap cleanup_test_cluster ERR INT #EXIT

# Test deployment
if [ ${NO_CHECK} = false ]; then
    # Setup cluster
    setup_test_cluster
    # Validation
    perform_test_deployment
    if [ ${KIND_CCM} = true ]; then
        # Setup LoadBalancer
        setup_kind_ccm
        # Validation
        perform_lb_deployment
    fi
    # Cleanup
    cleanup_test_cluster
fi

if [ ${ROOTLESS} = false ] && [ ${NO_CHECK} = false ]; then
    cat <<EOF

#########################################################################################################
##  Shell session should be reloaded MANUALLY to make the non-root user access to Docker take effect!  ##
#########################################################################################################
EOF
    fi

echo -e "\nSetup is finished."
exit ${RET_VAL}
