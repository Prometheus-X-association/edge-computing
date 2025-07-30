#!/usr/bin/env python3
# Copyright 2024 Janos Czentye
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
from __future__ import annotations

import logging
import subprocess

log = logging.getLogger(__package__)


def copy_image_to_registry(src_scheme: str, image: str, registry: str, with_reference: str = None,
                           src_auth: tuple[str, str] = None, dst_auth: tuple[str, str] = None,
                           insecure: bool = False, timeout: int = None) -> subprocess.CompletedProcess | None:
    log.info(f"Copying {image} to {registry}...")
    cmd = ['skopeo', 'copy']
    if logging.getLogger().level < logging.INFO:
        cmd.append('--debug')
    if src_auth:
        cmd.append('--src-creds={0}:{1}'.format(*src_auth))  # username[:password]
    if dst_auth:
        cmd.append('--dest-creds={0}:{1}'.format(*src_auth))  # username[:password]
    if insecure:
        cmd.append('--dest-tls-verify=false')
    match src_scheme:
        case 'docker' | 'remote':
            cmd.append(f'docker://{image}')
        case 'local':
            cmd.append(f'docker-daemon:{image}')
        case 'file' | 'tar':
            cmd.append(f'docker-archive:{image}')
    cmd.append(f'docker://{registry}/{with_reference if with_reference is not None else image}')
    log.debug(f"Assembled command: {' '.join(cmd)}")
    try:
        ret = subprocess.run(cmd, timeout=timeout, check=True)
    except (subprocess.CalledProcessError, subprocess.SubprocessError) as e:
        log.error(str(e))
        log.error("Failed to copy image to registry!")
        return None
    except subprocess.TimeoutExpired as e:
        log.error(f"Image copy timeout[{e.timeout}] expired!")
        log.error("Failed to copy image to registry!")
        return None
    else:
        log.info(f"Copied {image} to {registry} successfully!")
        return ret


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    copy_image_to_registry(src_scheme='docker', image='gcr.io/google-containers/pause:latest',
                           registry='registry.k3d.local:5000', with_reference='my-pause:latest', insecure=True,
                           timeout=10)
