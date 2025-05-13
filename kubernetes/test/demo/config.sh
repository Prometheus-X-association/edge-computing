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

SCRIPTS_DIR=$(readlink -f "$(dirname "$0")")
source "${SCRIPTS_DIR}/../scripts/helper.sh"

TIMEOUT=60s
CLUSTER=demo
NODE_A=node-a
NODE_B=node-b
NODE_AB=node-ab

PZ_A=zone-A
PZ_B=zone-B

API_IMG=ptx-edge/rest-api:1.0
BUILDER_IMG=ptx-edge/builder:1.0
PDC_IMG=ptx/connector:1.9.2-slim
MONGODB_IMG=ptx/mongodb:8.0.5-slim