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
IMG := "ptx-edge-api:0.1"
PORT := 8080
TEST := ptx-edge
API := rest-api
NPORT := 30080
CCM_NAME := kind-ccm
CCM_VER := v0.5.0
LB_PORT := 8080

setup:
	bash setup_kind_test_env.sh -xsc
	docker build -t ${IMG} mock-api/

create: setup
	kind create cluster -n ${CLUSTER} --wait=30s --config=manifests/kind_test_cluster_single.yaml
	kind load docker-image -n ${CLUSTER} ${IMG}

run2:
	kubectl create namespace ${TEST}
	kubectl -n ${TEST} run ${API} --image ${IMG} --image-pull-policy='Never' --port=${PORT}
	kubectl -n ${TEST} wait --for=condition=Ready --timeout=20s pod/${API}
	kubectl -n ${TEST} expose pod/${API} --type NodePort --target-port ${PORT} --name ${API} \
							--overrides='{"apiVersion":"v1","spec":{"ports":[{"nodePort":${NPORT},"port":${PORT}}]}}'
	kubectl -n ${TEST} get nodes,all,endpoints -o wide
	$(eval NODE_IP := `kubectl get node ${CLUSTER}-control-plane \
								-o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}'`)
	$(eval NODE_PORT := `kubectl get -n ${TEST} service/${API} -o jsonpath="{.spec.ports[].nodePort}"`)
	@echo
	@echo ">>> ${API} is available on http://${NODE_IP}:${NODE_PORT}/ptx-edge/v1/ui/"
	@curl -I "http://${NODE_IP}:${NODE_PORT}/ptx-edge/v1/ui/"
	@echo
	@echo ">>> ${API} is also exposed on http://localhost:${PORT}/ptx-edge/v1/ui/"
	@curl -I "http://localhost:${PORT}/ptx-edge/v1/ui/"

test2: | setup create run2

run3:
	kubectl create namespace ${TEST}
	kubectl label node ${CLUSTER}-control-plane node.kubernetes.io/exclude-from-external-load-balancers-
	docker run -q --rm -d --name ${CCM_NAME} --network kind \
				-v /var/run/docker.sock:/var/run/docker.sock \
				registry.k8s.io/cloud-provider-kind/cloud-controller-manager:${CCM_VER} -enable-lb-port-mapping
	kubectl -n ${TEST} run ${API} --image ${IMG} --image-pull-policy='Never' --port=${PORT}
	kubectl -n ${TEST} wait --for=condition=Ready --timeout=20s pod/${API}
	kubectl -n ${TEST} expose pod/${API} --type LoadBalancer --target-port ${PORT} --port ${LB_PORT}
	kubectl -n ${TEST} wait --for=jsonpath='{.status.loadBalancer.ingress}' --timeout=20s service/${API}
	kubectl -n ${TEST} get nodes,all,endpoints -o wide
	$(eval LB_IP = `kubectl get -n ${TEST} service/${API} -o jsonpath='{.status.loadBalancer.ingress[?(@.ip)].ip}'`)
	$(eval LB_IP_PORT = `docker ps -q -f "name=kindccm-*" | xargs -I {} -r docker port {} 8080 | head -1`)
	@echo
	@echo ">>> ${API} is available on http://${LB_IP}:${PORT}/ptx-edge/v1/ui/"
	@curl -I "http://${LB_IP}:${PORT}/ptx-edge/v1/ui/"
	@echo
	@echo ">>> ${API} is also exposed on http://${LB_IP_PORT}/ptx-edge/v1/ui/"
	@curl -I "http://${LB_IP_PORT}/ptx-edge/v1/ui/"

test3: | setup create run3

stop:
	kubectl -n ${TEST} delete all --all --now
	kubectl delete namespace ${TEST} --now
	docker ps -q -f "name=${CCM_NAME}" -f "name=kindccm-*" | xargs -r docker kill

cleanup:
	kind delete cluster -n ${CLUSTER}

tear-down: | stop cleanup

purge: cleanup
	docker images -q -f "reference=registry.k8s.io/cloud-provider-kind/*" -f "reference=envoyproxy/*" \
                    -f "reference=${TEST_IMG}" -f "reference=kindest/*" | xargs -r docker rmi -f

.PHONY: setup create run2 test2 run3 test3 stop cleanup tear-down purge
.DEFAULT_GOAL := test3
