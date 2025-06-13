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
API_IMG := ptx-edge/rest-api:1.0
REST_API := rest-api
API_PORT := 8080
PREFIX := ptx-edge/v1
BUILDER_IMG := ptx-edge/builder:1.0
BUILDER := builder
PDC_IMG := ptx/connector:1.9.2-slim
MONGODB_IMG := ptx/mongodb:8.0.5-slim
PDC := pdc
PDC_PORT := 3000
PDC_NODE_PORT := 30003
PDC_PREFIX := ptx-edge/pdc
SANDBOX := ptx-sandbox
CATALOG_IMG := ptx-sandbox/catalog:1.9.2-slim
CATALOG := catalog

build:
	bash setup_k3d_test_env.sh -xs
	${MAKE} -C ../src/rest-api/ build
	${MAKE} -C ../src/builder/ build
	${MAKE} -C ../src/ptx/ build

setup: build
	@#k3d cluster create ${CLUSTER} --wait --timeout=30s --config=manifests/k3d-test_cluster_single.yaml
	k3d cluster create ${CLUSTER} --wait --timeout=30s --config=manifests/k3d-test_cluster_multi.yaml
	@#k3d cluster create ${CLUSTER} --wait --timeout=30s --servers=1 --port="8080:80@loadbalancer"
	kubectl get nodes -o wide
	k3d image import -c ${CLUSTER} ${API_IMG} ${BUILDER_IMG} ${PDC_IMG} ${MONGODB_IMG} ${CATALOG_IMG}
	docker exec -ti k3d-test-cluster-server-0 crictl images | grep ptx

status:
	@k3d cluster list --no-headers | grep -q ^	# check for existing cluster
	@k3d cluster list
	@echo
	@kubectl get namespace ${PTX} --ignore-not-found -o wide || exit 0
	@kubectl get namespace ${SANDBOX} --ignore-not-found -o wide || exit 0
	@echo
	@kubectl get nodes -o wide || exit 0
	@echo
	@kubectl -n ${PTX} get \
		all,endpointslices,pv,pvc,configmaps,secrets,ingress,ingressroute.traefik.io,middleware.traefik.io \
		--ignore-not-found -o wide || exit 0
	@echo
	@kubectl -n ${PTX} top pod || exit 0
	@kubectl -n ${PTX} top pod --containers || exit 0
	@echo
	@kubectl -n ${PTX} top node || exit 0

view:
	@bash ./scripts/start-kube-ops-view.sh

run-huge-pods:
	kubectl create namespace ${PTX}
	kubectl -n ${PTX} apply -f manifests/ptx-edge-chuge_test_pod.yaml
	kubectl -n ${PTX} apply -f manifests/ptx-edge-mhuge_test_pod.yaml
	@echo "\n>>> Waiting for potential escalation...\n" && sleep 3s
	@#kubectl -n ${PTX} events --for=pod/cpu-huge-pod
	@#kubectl -n ${PTX} events --for=pod/mem-huge-pod
	kubectl -n ${PTX} events --types=Warning
	kubectl -n ${PTX} top node

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
	kubectl -n ${PTX} get nodes,all,endpointslices,ingress,pv,pvc -o wide
	@echo "Waiting for ingress to set up..." && sleep 10
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

test-api: | build setup run-api

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

test-builder: | build setup run-builder

run-pdc:
	${MAKE} -C ./ptx/ run-catalog
	kubectl create namespace ${PTX}
	kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_config.yaml
	kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_deployment.yaml
	kubectl -n ${PTX} wait --for="condition=Available" --timeout=20s deployment/${PDC}
	kubectl -n ${PTX} create service nodeport ${PDC} --tcp=${PDC_PORT}:${PDC_PORT} --node-port=${PDC_NODE_PORT}
	@#kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_nodeport.yaml
	kubectl -n ${PTX} wait --for=jsonpath='{.spec.clusterIP}' --timeout=20s service/${PDC}
	kubectl -n ${PTX} get all,configmaps,secrets,endpointslices -o wide
	$(eval NODE_IP = `kubectl -n ${PTX} get pod -l app=${PDC} -o jsonpath='{.items[].status.hostIP}'`)
	@echo "Waiting for PDC to set up..."
	@#timeout 3 grep -m1 "Server running on" <(kubectl -n ${PTX} logs deployments/${PDC} -fc ptx-connector)	# needs bash
	( kubectl -n ${PTX} logs -f deployments/${PDC} -c ptx-connector & ) | timeout 60 grep -m1 "Server running on"
	@echo
	@echo ">>> ${PDC} is exposed on http://${NODE_IP}:${PDC_NODE_PORT}/"
	@curl -I "http://${NODE_IP}:${PDC_NODE_PORT}/"
	curl -Ssf "http://${NODE_IP}:${PDC_NODE_PORT}/" | grep "href"

test-pdc: | build setup run-pdc

run-pdc-ingress:
	${MAKE} -C ./ptx/ run-catalog
	kubectl create namespace ${PTX}
	kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_config.yaml
	kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_deployment_ingress.yaml
	kubectl -n ${PTX} wait --for="condition=Available" --timeout=20s deployment/${PDC}
	### Setup ingress
	@#kubectl -n ${PTX} expose deployment/${PDC} --target-port ${PDC_PORT} --port ${PDC_PORT} --name ${PDC}
	kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_service.yaml
	kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_ingressroute.yaml
	#kubectl -n ${PTX} wait --for=jsonpath='{.status.loadBalancer.ingress[].ip}' --timeout=30s ingress/${PDC}
	kubectl -n ${PTX} get nodes,all,endpointslices,ingressroute.traefik.io,middleware.traefik.io -o wide
	echo "Waiting for PDC to set up..."
	( kubectl -n ${PTX} logs -f deployments/${PDC} -c ptx-connector & ) | timeout 60 grep -m1 "Server running on"
	@echo
	@echo ">>> ${PDC} is exposed on http://localhost:8080/ptx-edge/pdc"
	@curl -I "http://localhost:8080/ptx-edge/pdc"
	curl -Ssf "http://localhost:8080/ptx-edge/pdc" | grep "href"

run-pdc-daemon:
	${MAKE} -C ./ptx/ run-catalog
	kubectl create namespace ${PTX}
	kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_config.yaml
	kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_daemonset.yaml
	kubectl -n ${PTX} wait --for=jsonpath='.status.numberReady'=2 daemonset/${PDC}
	kubectl -n ${PTX} get all,configmaps,secrets -o wide
	echo "Waiting for PDC instances to set up..."
	( \
		for pod in $$(kubectl -n ${PTX} get pods -l app=${PDC} -o jsonpath='{.items[*].metadata.name}'); do \
			( kubectl -n ${PTX} logs -f pods/$${pod} -c ptx-connector & ) | timeout 90 grep -m1 "Server running on"; \
		done; \
	)
	( \
		for node in $$(kubectl -n ${PTX} get pods -l app=${PDC} -o jsonpath='{.items[*].status.hostIP}'); do \
			echo "\n>>> PDC instance is exposed on http://$${node}:${PDC_NODE_PORT}/"; \
			curl -Ssf -I "http://$${node}:${PDC_NODE_PORT}/"; \
		done; \
	)

run-pdc-sandboxed:
	### Setup sandbox namespace
	kubectl create namespace ${SANDBOX}
	kubectl -n ${SANDBOX} apply -f manifests/ptx-sandbox-deployment.yaml
	kubectl -n ${SANDBOX} wait --for="condition=Available" --timeout=20s deployment/${CATALOG}
	kubectl -n ${SANDBOX} get all
	### Deploy PDC
	kubectl create namespace ${PTX}
	kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_config.yaml -l app.kubernetes.io/component!=cfg-envvars
	kubectl -n ${PTX} apply -f manifests/ptx-sandbox-pdc_env.yaml
	kubectl -n ${PTX} apply -f manifests/ptx-edge-pdc_deployment.yaml
	kubectl -n ${PTX} wait --for="condition=Available" --timeout=20s deployment/${PDC}
	kubectl -n ${PTX} create service nodeport ${PDC} --tcp=${PDC_PORT}:${PDC_PORT} --node-port=${PDC_NODE_PORT}
	kubectl -n ${PTX} wait --for=jsonpath='{.spec.clusterIP}' --timeout=20s service/${PDC}
	kubectl -n ${PTX} get all,configmaps,secrets,endpointslices -o wide
	$(eval NODE_IP = `kubectl -n ${PTX} get pod -l app=${PDC} -o jsonpath='{.items[].status.hostIP}'`)
	@echo "Waiting for PDC to set up..."
	@#timeout 3 grep -m1 "Server running on" <(kubectl -n ${PTX} logs deployments/${PDC} -fc ptx-connector)	# needs bash
	( kubectl -n ${PTX} logs -f deployments/${PDC} -c ptx-connector & ) | timeout 60 grep -m1 "Server running on"
	@echo
	@echo ">>> ${PDC} is exposed on http://${NODE_IP}:${PDC_NODE_PORT}/"
	@curl -I "http://${NODE_IP}:${PDC_NODE_PORT}/"
	curl -Ssf "http://${NODE_IP}:${PDC_NODE_PORT}/" | grep "href"

stop:
	@#kubectl -n ${PTX} delete all --all --now
	kubectl delete namespace ${PTX} --ignore-not-found --now || exit 0
	kubectl delete namespace ${SANDBOX} --ignore-not-found --now || exit 0
	kubectl delete pv,pvc,ingress --all --ignore-not-found --force || exit 0
	docker ps -aq -f name=ptx-catalog | xargs -r docker rm -f || exit 0
	docker container prune -f || exit 0

cleanup:
	k3d cluster delete ${CLUSTER} || exit 0

tear-down: | stop cleanup

purge: cleanup
	docker image ls -q -f "reference=ghcr.io/k3d-io/*" -f "reference=rancher/*" \
		-f "reference=${PTX}/*" | xargs -r docker rmi -f

.PHONY: build setup status run-huge-pods run-api test-api run-builder test-builder run-pdc test-pdc \
			run-pdc-ingress run-pdc-daemon run-pdc-sandboxed stop cleanup tear-down purge
.DEFAULT_GOAL := setup
