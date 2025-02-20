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

while getopts ":u" flag; do
	case "${flag}" in
        u)
            echo "[x] Update to the latest versions."
            UPDATE=true
            ;;
        ?)
            echo "Invalid parameter: -${OPTARG} !"
            exit 1;;
    esac
done

echo "Install test dependencies..."

sudo apt update && sudo apt install -y shunit2

if [[ -v UPDATE ]]; then
    pushd "$(mktemp -d)" || exit 1
    git clone https://github.com/kward/shunit2
    sudo install -v ./shunit2/shunit2 ./shunit2/shunit2_test_helpers /usr/share/shunit2/
    popd || exit 1
fi

echo "Done."