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

dependencies:
	@bash setup_k3d_env.sh

setup:
	@bash setup.sh

deploy:
	@bash setup.sh -d

remove:
	@bash setup.sh -r

status:
	@bash setup.sh -s

teardown:
	@bash setup.sh -c

redeploy:
	@bash setup.sh -x

.PHONY: setup deploy remove status teardown redeploy
.DEFAULT_GOAL := setup