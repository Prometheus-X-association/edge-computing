# Copyright 2026 Janos Czentye
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

run-simple-api ::
	./run_simple_api.sh || true

deploy-api-http ::
	./deploy_datasource_api.sh || true

deploy-api-https ::
	./deploy_datasource_api.sh -s || true

########################################################################################################################

ngrok-tunnel-http ::
	./create_ngrok_tunnel.sh 9080

ngrok-tunnel-https ::
	./create_ngrok_tunnel.sh https://localhost:9443

ngrok-tunnel-pdc ::
	./create_ngrok_tunnel.sh 3000

stop-ngrok-tunnel ::
	docker ps -aq -f name="ngrok-tun-*" | xargs -r docker rm --force || true

########################################################################################################################

start-pdc ::
	./setup_connector.sh

########################################################################################################################

status ::
	@docker ps -f label="role.dataspace.ptx.org=datasource"

cleanup ::
	docker ps -aq -f label="role.dataspace.ptx.org=datasource" | xargs -r docker rm --force || true

########################################################################################################################

setup :: | cleanup deploy-api-https start-pdc ngrok-tunnel-pdc status

########################################################################################################################

#.SILENT:	# Set silent mode (-s) by default
.PHONY:		# Set all target phony
.DEFAULT_GOAL := setup