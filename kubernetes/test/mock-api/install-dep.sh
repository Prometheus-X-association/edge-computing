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
# limitations under the License
PY_VERSION=python3.12

if ! command -v ${PY_VERSION} >/dev/null 2>&1; then
    sudo apt install -y software-properties-common make
    echo -e "\nInstalling ${PY_VERSION}...\n"
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt install -y ${PY_VERSION} ${PY_VERSION}-venv
    ${PY_VERSION} -V
    echo -e "\nInstalling pip for ${PY_VERSION}...\n"
    ${PY_VERSION} -m ensurepip --upgrade
fi