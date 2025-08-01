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
TEST_LEVEL := level4

setup:
	${MAKE} -C kubernetes/test/levels/${TEST_LEVEL} setup

run:
	${MAKE} -C kubernetes/test/levels/${TEST_LEVEL} run

cleanup:
	${MAKE} -C kubernetes/test/levels/${TEST_LEVEL} tear-down

tests:
	cd kubernetes/test/units && ./runall.sh -d -o ./results
	cd kubernetes/test/suites && ./runall.sh -o ./results

.PHONY: setup run cleanup tests
.DEFAULT_GOAL := run
