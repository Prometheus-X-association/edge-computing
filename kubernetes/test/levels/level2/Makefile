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
CLUSTER := ptx-edge-test
IMG := ptx-edge-api:0.1
PORT := 8080
TEST := ptx-edge
API := rest-api
NPORT := 30080

setup:
	bash ../../setup_kind_test_env.sh -xs
	docker build -t ${IMG} ../../mock-api/

create: setup
	kind create cluster -n ${CLUSTER} --wait=30s --config=../../manifests/kind-test_cluster_single.yaml
	kubectl get nodes -o wide
	kind load docker-image -n ${CLUSTER} ${IMG}

run:
	kubectl create namespace ${TEST}
	kubectl -n ${TEST} run ${API} --image ${IMG} --image-pull-policy='Never' --port=${PORT}
	kubectl -n ${TEST} wait --for=condition=Ready --timeout=20s pod/${API}
	kubectl -n ${TEST} expose pod/${API} --type NodePort --target-port ${PORT} --name ${API} \
							--overrides='{"apiVersion":"v1","spec":{"ports":[{"nodePort":${NPORT},"port":${PORT}}]}}'
	kubectl -n ${TEST} get all,endpoints -o wide
	$(eval NODE_IP := `kubectl get node/${CLUSTER}-control-plane \
								-o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}'`)
	$(eval NODE_PORT := `kubectl get -n ${TEST} service/${API} -o jsonpath="{.spec.ports[].nodePort}"`)
	@echo
	@echo ">>> ${API} is available on http://${NODE_IP}:${NODE_PORT}/ptx-edge/v1/ui/"
	@curl -I "http://${NODE_IP}:${NODE_PORT}/ptx-edge/v1/ui/"
	@echo
	@echo ">>> ${API} is also exposed on http://localhost:${PORT}/ptx-edge/v1/ui/"
	@curl -I "http://localhost:${PORT}/ptx-edge/v1/ui/"

test: | setup create run

stop:
	kubectl -n ${TEST} delete all --all --now || exit 0
	kubectl delete namespace ${TEST} --now || exit 0

cleanup:
	kind delete cluster -n ${CLUSTER} || exit 0

purge: cleanup
	docker images -q -f "reference=${TEST_IMG}" -f "reference=kindest/*" | xargs -r docker rmi -f

.PHONY: setup create run test stop cleanup purge
.DEFAULT_GOAL := create
