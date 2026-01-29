#!/usr/bin/env bash
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

sudo apt install -y apt-transport-https wget gettext

KCOLOR_VER="$(wget -q -O- https://kubecolor.github.io/packages/deb/version)_$(dpkg --print-architecture)"
wget -O /tmp/kubecolor.deb "https://kubecolor.github.io/packages/deb/pool/main/k/kubecolor/kubecolor_${KCOLOR_VER}.deb"
sudo dpkg -i /tmp/kubecolor.deb