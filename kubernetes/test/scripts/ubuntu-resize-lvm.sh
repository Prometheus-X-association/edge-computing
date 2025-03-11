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

set -eou pipefail

SCRIPT_DIR=$(readlink -f "$(dirname "$0")")
LV_DEV=/dev/ubuntu-vg/ubuntu-lv
LV_SIZE=100

source "${SCRIPT_DIR}"/helper.sh

LOG "Resize LVM to use all VM partition size"

source /etc/lsb-release
if ! [ "${DISTRIB_RELEASE}" = 24.04 ]; then
    echo "LVM resizing on Ubuntu version (${DISTRIB_RELEASE}) other than 24.04 is not tested. Exiting..."
    exit 1
fi

df -hTlP | grep '/dev/.*lv.*/' -A10 -B10

log "LVM settings"
sudo pvdisplay
sudo vgdisplay
sudo lvdisplay

log "Check for device based on volume group and logical volume (default LVM setting: ${LV_DEV})"
if ! [ -e /dev/ubuntu-vg/ubuntu-lv ]; then
    echo "Default logical volume not found! Exiting..."
    exit 1
fi
ls -al ${LV_DEV}

log "Resizing logical volume..."
sudo lvextend -l +${LV_SIZE}%FREE ${LV_DEV}

log "Resizing file system..."
sudo resize2fs ${LV_DEV}

log "New logical volume:"
df -hTlP | grep '/dev/.*lv.*/' -A10 -B10

echo "Done."

