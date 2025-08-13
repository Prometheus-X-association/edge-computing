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
export REGISTRY := registry.k3d.local
export LOCAL_REGISTRY := registry.k3d.localhost
REGISTRY_USER := demo
REGISTRY_SECRET := demo
CRED := ${REGISTRY_USER}:${REGISTRY_SECRET}

NAME := registry
VERSION := 1.0
IMG := ptx-edge/${NAME}:${VERSION}

cert:
	rm -rf ${CURDIR}/.certs && mkdir -p ${CURDIR}/.certs/ca && mkdir -p ${CURDIR}/.certs/auth
	@#openssl req -x509 -newkey rsa:2048 -sha256 -keyout .certs/registry.key -out .certs/registry.cert -days 365 -noenc \
	# -subj "/C=EU/ST=''/L=''/O=PTX/OU=ptx-edge/CN=registry.k3d.local"
	openssl genrsa -out ${CURDIR}/.certs/ca.key 2048
	openssl req -new -x509 -days 365 -key ${CURDIR}/.certs/ca.key -out ${CURDIR}/.certs/ca/ca.crt \
			-subj "/C=EU/ST=''/L=''/O=PTX/OU=dataspace/CN=dataspace.prometheus-x.org"
	openssl req -newkey rsa:2048 -noenc -keyout ${CURDIR}/.certs/auth/server.key -out ${CURDIR}/.certs/server.csr \
			-subj "/C=EU/ST=''/L=''/O=ptx-edge/OU=ptx-edge/CN=*ptx-edge.prometheus-x.org"
	printf "subjectAltName=DNS:$${REGISTRY},DNS:$${LOCAL_REGISTRY}" | openssl x509 -req -days 365 \
			-in ${CURDIR}/.certs/server.csr -CA ${CURDIR}/.certs/ca/ca.crt -CAkey ${CURDIR}/.certs/ca.key \
			-out ${CURDIR}/.certs/auth/server.cert -extfile=- #-CAcreateserial
	@#docker run --entrypoint htpasswd httpd:2 -Bbn demo demo > .certs/htpasswd
	htpasswd -Bbn ${REGISTRY_USER} ${REGISTRY_SECRET} > ${CURDIR}/.certs/auth/htpasswd
	@#curl -k -u demo:demo https://localhost:5555/v2/_catalog
	@#wget -O- --no-check-certificate --user=demo --password=demo https://localhost:5555/v2/_catalog
	@#
	@#curl --cacert .certs/ca/ca.crt -u demo:demo https://registry.k3d.localhost:5555/v2/_catalog
	@#curl --cacert .certs/ca/ca.crt -u demo:demo --resolve registry.k3d.local:5555:127.0.0.1 https://registry.k3d.local:5555/v2/_catalog
	@#wget -O- --ca-certificate=.certs/ca/ca.crt --user=demo --password=demo https://registry.k3d.localhost:5555/v2/_catalog
	@#skopeo inspect --cert-dir=.certs/ca --creds=demo:demo docker://registry.k3d.localhost:5555/busybox:latest

build: cert
	docker build -t ${IMG} .
	docker images --no-trunc ${IMG}

run: build
	docker run --rm -ti -p 5555:5000 --restart=no --name ptx-registry \
		-v ${CURDIR}/.certs/auth:/opt/registry/auth:ro \
		-e "REGISTRY_AUTH=htpasswd" -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm" \
		-e "REGISTRY_AUTH_HTPASSWD_PATH=/opt/registry/auth/htpasswd" \
		-e "REGISTRY_HTTP_TLS_CERTIFICATE=/opt/registry/auth/server.cert" \
		-e "REGISTRY_HTTP_TLS_KEY=/opt/registry/auth/server.key" \
		registry:3

test: clear
	docker run -d -p 5678:5000 --restart=no --name test-registry \
		-v ${CURDIR}/.certs/auth:/opt/registry/auth:ro \
		-e "REGISTRY_AUTH=htpasswd" -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm" \
		-e "REGISTRY_AUTH_HTPASSWD_PATH=/opt/registry/auth/htpasswd" \
		-e "REGISTRY_HTTP_TLS_CERTIFICATE=/opt/registry/auth/server.cert" \
		-e "REGISTRY_HTTP_TLS_KEY=/opt/registry/auth/server.key" \
		registry:3
	docker pull busybox:latest
	docker login -u ${REGISTRY_USER} -p ${REGISTRY_SECRET} ${LOCAL_REGISTRY}:5678
	docker tag busybox:latest ${LOCAL_REGISTRY}:5678/busybox:latest
	docker push ${LOCAL_REGISTRY}:5678/busybox:latest
	docker rmi ${LOCAL_REGISTRY}:5678/busybox:latest
	docker logout ${LOCAL_REGISTRY}:5678
	@printf "\nShow certificates:\n"
	openssl s_client -showcerts -connect ${LOCAL_REGISTRY}:5678 </dev/null
	@printf "\nCheck registry:\n"
	curl --cacert .certs/ca/ca.crt -u ${CRED} https://registry.k3d.localhost:5678/v2/_catalog
	@echo
	wget -qO- --ca-certificate=.certs/ca/ca.crt --user=${REGISTRY_USER} --password=${REGISTRY_SECRET} \
			https://registry.k3d.localhost:5678/v2/_catalog
	@echo
	skopeo inspect --cert-dir=.certs/ca --creds=${CRED} docker://${LOCAL_REGISTRY}:5678/busybox:latest

########################################################################################################################

docker-test-setup: build

docker-unit-tests: docker-test-setup
	@echo ">>> No docker unit test is defined for local k3d registry!"

unit-tests:
	@echo ">>> No local unit test is defined for local k3d registry!"

########################################################################################################################

clear:
	-docker rm -f test-registry ptx-registry

purge: clear
	rm -rf ${CURDIR}/.certs
	docker rmi -f ${IMG}

.PHONY:
.DEFAULT_GOAL := cert