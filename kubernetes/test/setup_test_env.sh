#!/usr/bin/env bash

# Copyright 2024 Janos Czentye
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

#--------------------------------------------------------------------------------

KIND_VER=v0.24.0
#KUBECTL_VER=$(curl -L -s https://dl.k8s.io/release/stable.txt)
KUBECTL_VER=v1.31.0	# used by Kind v0.24.0

ROOTLESS=false

TEST_K8S='test-cluster'
TEST_NS='ptx-edge'
TEST_ID='test42'
TEST_IMG='busybox:1.36'
TEST_CMD='echo "Waiting to exit..." && sleep infinity'
TEST_OK='Running'

PZ_LAB='privacy-zone.dataspace.prometheus-x.org'
RET_VAL=0


#--------------------------------------------------------------------------------

while getopts r flag; do
	case "${flag}" in
		r)
			ROOTLESS=true
			cat << EOF

Rootless setup is configured...

It may cause performance degradation of misbehavior due to different restrictions!
See more:
	- https://docs.docker.com/engine/security/rootless/#known-limitations
	- https://kind.sigs.k8s.io/docs/user/rootless/#restrictions

EOF
			sleep 3s;;
	  *)
	    echo "Invalid parameter: $flag"
	    exit 1;;
	esac
done

#--------------------------------------------------------------------------------

echo ">>> Setup dependencies..."

# Check docker install
if ! command -v docker >/dev/null; then
	echo
	echo ">>> Install Docker..."
	echo
	sudo apt-get update && sudo apt-get install -y ca-certificates curl
	curl -fsSL https://get.docker.com/ | sh

	if [ $ROOTLESS = true ]; then
		# Rootless Docker
		sudo apt-get update && sudo apt-get install -y uidmap
		dockerd-rootless-setuptool.sh install
		sudo loginctl enable-linger ubuntu
		echo -e "\n# Rootless docker\nexport DOCKER_HOST=unix:///run/user/1000/docker.sock" >> ~/.bashrc
		source ~/.bashrc

		# Add support for Ubuntu 24.04
		source /etc/lsb-release
		if [ "$DISTRIB_RELEASE" = 24.04 ]; then
			filename=$(echo "$HOME"/bin/rootlesskit | sed -e s@^/@@ -e s@/@.@g)
			cat <<EOF > ~/"$filename"
abi <abi/4.0>,
include <tunables/global>

"$HOME/bin/rootlesskit" flags=(unconfined) {
  userns,

  include if exists <local/${filename}>
}
EOF
			sudo mv ~/"$filename" /etc/apparmor.d/"$filename"
			sudo systemctl restart apparmor.service
		fi
	else
		# Privileged Docker
		sudo usermod -aG docker "$USER"
		echo
		echo ">>> Jump into new shell for docker group privilege..." && sleep 3s
		echo
		exec sg docker "$0" "$@"
	fi
else
	echo
	echo ">>> Check Docker install..."
	echo
	docker run --rm hello-world
fi


# Install kind
if ! command -v kind >/dev/null; then
	# Binary
	echo
	echo ">>> Install Kind binary..."
	echo
	sudo apt-get update && sudo apt-get install -y curl
	[ "$(uname -m)" = x86_64 ] && curl -Lo ./kind "https://kind.sigs.k8s.io/dl/$KIND_VER/kind-linux-amd64"
	chmod +x ./kind
	sudo mv -v ./kind /usr/local/bin/kind

	# Bash completion
	echo
	echo ">>> Install bash completion..."
	echo
	sudo apt-get install -y bash-completion
	mkdir -p /etc/bash_completion.d
	kind completion bash | sudo tee /etc/bash_completion.d/kind-completion > /dev/null
	sudo chmod a+r /etc/bash_completion.d/kind-completion
	source ~/.bashrc

	# Rootless Kind
	if [ $ROOTLESS = true ]; then
		sudo su -c "mkdir -p /etc/systemd/system/user@.service.d/ &&
			echo -e '[Service]\nDelegate=yes' > /etc/systemd/system/user@.service.d/delegate.conf"
		sudo su -c "mkdir -p /etc/modules-load.d/ &&
			echo -e 'ip6_tables\nip6table_nat\nip_tables\niptable_nat' > /etc/modules-load.d/iptables.conf"
		sudo systemctl daemon-reload
		sudo sysctl -w kernel.dmesg_restrict=0
		systemctl --user restart docker
	fi

	echo
	(set -x; kind version)
fi

# Check kubectl
if ! command -v kubectl >/dev/null; then
	# Binary
	echo
	echo ">>> Installing kubectl..."
	echo
	curl -LO "https://dl.k8s.io/release/$KUBECTL_VER/bin/linux/amd64/kubectl"
	sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

	# Bash completion
	kubectl completion bash | sudo tee /etc/bash_completion.d/kubectl > /dev/null
	sudo chmod a+r /etc/bash_completion.d/kubectl

	echo
	(set -x; kubectl version --client)
fi

#--------------------------------------------------------------------------------

cleanup_cluster () {
	echo ">>> Cleanup..."
	#kubectl delete pod ${TEST_ID} -n ${TEST_NS} --grace-period=0 #--force
	kind delete cluster -n ${TEST_K8S}
}

# Register cleanup
trap cleanup_cluster ERR #EXIT

# Setup cluster
echo
echo ">>> Prepare test cluster with id: $TEST_K8S..."
echo
cat <<EOF | kind create cluster -n "$TEST_K8S" --wait=30s --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: $TEST_K8S
nodes:
  - role: control-plane
    labels:
      $PZ_LAB/zone-C: true
  - role: worker
    labels:
      $PZ_LAB/zone-A: true
      $PZ_LAB/zone-B: true
  - role: worker
    labels:
      $PZ_LAB/zone-B: true
EOF

echo
echo ">>> Kind cluster info:"
echo
kubectl cluster-info --context kind-${TEST_K8S}
echo
echo ">>> K8s setup:"
echo
kubectl version
echo
kubectl get all -n kube-system
echo
kubectl get nodes -o wide -L ${PZ_LAB}/zone-A -L ${PZ_LAB}/zone-B -L ${PZ_LAB}/zone-C

# Validate control plane
echo
echo ">>> Perform a test deployment..."
echo
set -x
docker pull ${TEST_IMG}
kind load docker-image -n ${TEST_K8S} ${TEST_IMG}
kubectl create namespace ${TEST_NS}
kubectl run ${TEST_ID} -n ${TEST_NS} --image ${TEST_IMG} --image-pull-policy='Never' --restart='Never' \
		--overrides='{"apiVersion":"v1","spec":{"nodeSelector":{'\"${PZ_LAB}'/zone-A":"true"}}}' -- /bin/sh -c "$TEST_CMD"
kubectl wait -n ${TEST_NS} --for=condition=Ready --timeout=10s pod/${TEST_ID}
set +x

echo
echo ">>> Waiting for potential escalation..." && sleep 3s
echo
kubectl get pods ${TEST_ID} -n ${TEST_NS} -o wide

echo
if [[ "$(kubectl get pods ${TEST_ID} -n ${TEST_NS} -o jsonpath=\{.status.phase\})" == "$TEST_OK" ]]; then
	echo ">>> Setup OK!"
else
	echo ">>> Setup failed!"
	kind export logs "./$TEST_ID-failed" -n ${TEST_NS} --verbosity=2
	RET_VAL=1
fi
echo

# Cleanup
cleanup_cluster

if [ ! $ROOTLESS = true ]; then
	echo
	echo -e "\nReload shell session MANUALLY to make the non-root user access (no sudo) to Docker take effect!"
	echo
fi

echo "Done."
exit ${RET_VAL}
