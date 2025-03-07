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

CLUSTER := test-cluster
PTX := ptx-edge
API_IMG := "ptx-edge/rest-api:1.0"
REST_API := rest-api
API_PORT := 8080
PREFIX := ptx-edge/v1
BUILDER_IMG := "ptx-edge/builder:1.0"
BUILDER := builder

setup:
	bash setup_k3d_test_env.sh -xs
	@#cd ../src/rest-api/ && make build
	@#cd ../src/builder/ && make build
	${MAKE} -C ../src/rest-api/ build
	${MAKE} -C ../src/builder/ build

create: setup
	@#k3d cluster create ${CLUSTER} --wait --timeout=30s --config=manifests/k3d-test_cluster_single.yaml
	k3d cluster create ${CLUSTER} --wait --timeout=30s --config=manifests/k3d-test_cluster_multi.yaml
	@#k3d cluster create ${CLUSTER} --wait --timeout=30s --servers=1 --port="8080:80@loadbalancer"
	kubectl get nodes -o wide
	k3d image import -c ${CLUSTER} ${API_IMG} ${BUILDER_IMG}

status:
	k3d cluster list && return 0
	@echo
	kubectl get namespace ${PTX} --ignore-not-found -o wide || exit 0
	@echo
	kubectl -n ${PTX} get all,ingress,pv,pvc --ignore-not-found -o wide  || exit 0

run-api:
	### Setup rest-api
	kubectl create namespace ${PTX}
	kubectl -n ${PTX} create deployment ${REST_API} --image ${API_IMG} --replicas=1 --port=${API_PORT}
	kubectl -n ${PTX} wait --for="condition=Available" --timeout=20s deployment/${REST_API}
	kubectl -n ${PTX} expose deployment/${REST_API} --target-port ${API_PORT} --port ${API_PORT} --name ${REST_API}
	### Setup ingress
	kubectl -n ${PTX} create ingress ${REST_API} --rule="/${PREFIX}/*=${REST_API}:${API_PORT},tls" --class=traefik \
	 	--default-backend="${REST_API}:${API_PORT}" --annotation="ingress.kubernetes.io/ssl-redirect=false"
	kubectl -n ${PTX} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout=30s ingress/${REST_API}
	kubectl -n ${PTX} get nodes,all,endpoints,ingress,pv,pvc -o wide
	@ echo "Waiting for ingress to set up..." && sleep 10
	$(eval INGRESS_IP = `kubectl -n ${PTX} get ingress/${REST_API} -o jsonpath='{.status.loadBalancer.ingress[].ip}'`)
	@echo
	@echo ">>> ${REST_API} is exposed on http://${INGRESS_IP}:80/${PREFIX}/ui/"
	@curl -I "http://${INGRESS_IP}:80/${PREFIX}/ui/"
	@echo
	@echo ">>> ${REST_API} is exposed on https://${INGRESS_IP}:443/${PREFIX}/ui/"
	@curl -I -k "https://${INGRESS_IP}:443/${PREFIX}/ui/"
	@echo
	@echo ">>> ${REST_API} is also exposed on http://localhost:8080/${PREFIX}/ui/"
	@curl -I "http://localhost:8080/${PREFIX}/ui/"
	curl -LSs "http://localhost:8080/${PREFIX}/versions" | python3 -m json.tool

test-api: | setup create run-api

run-builder:
	kubectl create namespace ${PTX}
	@#kubectl -n ${PTX} create job ${BUILDER} --image ${BUILDER_IMG}
	kubectl -n ${PTX} apply -f manifests/ptx-edge-builder_worker_pvc.yaml
	kubectl -n ${PTX} apply -f manifests/ptx-edge-builder_worker_job.yaml
	kubectl -n ${PTX} wait --for='jsonpath={.status.phase}=Bound' --timeout=20s pvc/worker-pvc
	kubectl -n ${PTX} get all,pv,pvc -o wide
	kubectl -n ${PTX} wait --for="condition=Complete" --timeout=20s job/${BUILDER}
	kubectl -n ${PTX} get all -o wide
	kubectl -n ${PTX} logs job/${BUILDER} --all-containers

test-builder: | setup create run-builder

stop:
	@#kubectl -n ${PTX} delete all --all --now
	kubectl delete namespace ${PTX} --ignore-not-found --now
	kubectl delete pv,pvc,ingress --all --ignore-not-found --force

cleanup:
	k3d cluster delete ${CLUSTER}

tear-down: | stop cleanup

purge: cleanup
	docker image ls -q -f "reference=ghcr.io/k3d-io/*" -f "reference=rancher/*" \
		-f "reference=${PTX}/*" | xargs -r docker rmi -f

.PHONY: setup create status run-api test-api run-builder test-builder stop cleanup tear-down purge
.DEFAULT_GOAL := test3
