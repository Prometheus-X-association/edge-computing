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

TEST_ID="test42"
TEST_IMG="busybox:1.36"
TEST_CMD="echo 'Waiting to exit...' && sleep infinity"
TEST_OK="Running"
RET_VAL=0

echo ">>> Setup Kind..."

# Check docker install
if ! command -v docker >/dev/null; then
	echo ">>> Docker is missing!"
	sudo apt-get update && sudo apt-get install -y ca-certificates curl
	curl -fsSL https://get.docker.com/ | sh
	sudo usermod -aG docker ${USER}
	docker run --rm hello-world
fi

# Install kind
if ! command -v kind >/dev/null; then
	# Binary
	echo
	echo ">>> Install Kind binary..."
	echo
	sudo apt-get update && sudo apt-get install -y curl
	[ $(uname -m) = x86_64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.24.0/kind-linux-amd64
	chmod +x ./kind
	sudo mv -v ./kind /usr/local/bin/kind

	# Completion
	echo
	echo ">>> Install bash completion..."
	echo
	sudo apt-get install -y bash-completion
	mkdir -p /etc/bash_completion.d
	kind completion bash | sudo tee /etc/bash_completion.d/kind-completion > /dev/null
fi

# Setup cluster
echo
echo ">>> Prepare test cluster"
echo
kind create cluster -n ${TEST_ID} --wait=30s #--verbosity=2
echo
kubectl cluster-info --context kind-${TEST_ID}
echo
kubectl get all -n kube-system

# Validate control plane
echo
echo ">>> Perform test deployment"
echo
docker pull ${TEST_IMG}
kind load docker-image -n ${TEST_ID} ${TEST_IMG}
kubectl run ${TEST_ID} --image ${TEST_IMG} --restart='Never' -- /bin/sh -c "$TEST_CMD"
kubectl wait --for=condition=Ready --timeout=10s pod/${TEST_ID}

echo
echo ">>> Waiting for potential escalation..." && sleep 3s
echo
kubectl get pods ${TEST_ID} -o wide

if [[ $(kubectl get pods ${TEST_ID} -o jsonpath={.status.phase}) == ${TEST_OK} ]]; then
	echo
	echo ">>> Setup OK!"
	echo
else
	echo
	echo ">>> Setup failed!"
	echo
	RET_VAL=1
fi


# Cleanup
echo ">>> Cleanup..."
kubectl delete pod ${TEST_ID} #--force
kind delete cluster -n ${TEST_ID}

echo ">>> Done"
exit ${RET_VAL}
