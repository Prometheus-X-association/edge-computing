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

install: mock-api/Dockerfile
	# bash setup_kind_test_env.sh -xs
	docker build -t ptx-edge-api:0.1 mock-api/

run: install
	# bash create_test_cluster.sh
	docker run --rm --name ptx-edge-api -p 8080:8080 -it ptx-edge-api:0.1

cleanup:
	# kind delete cluster -n "test"
	docker rmi -f ptx-edge-api:0.1

.PHONY: install run cleanup
.DEFAULT_GOAL := run
