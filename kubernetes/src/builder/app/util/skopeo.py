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

import json
import logging
import subprocess

log = logging.getLogger(__package__)


def inspect_image(registry: str, image: str, user: str = None, passwd: str = None, insecure: bool = False,
                  timeout: int = None) -> dict | None:
    """

    :param registry:
    :param image:
    :param user:
    :param passwd:
    :param insecure:
    :param timeout:
    :return:
    """
    log.info(f"Validating {image} in {registry}...")
    cmd = ['skopeo', 'inspect']
    if user:
        cmd.append(f"--username={user}")
        if passwd:
            cmd.append(f"--password={passwd}")
    if insecure:
        cmd.append('--tls-verify=false')
    if timeout:
        cmd.append(f"--command-timeout={timeout}")
    cmd.append(f"docker://{registry}/{image}")
    log.debug(f"Assembled command: {' '.join(cmd)}")
    try:
        ret = subprocess.run(cmd, stdout=subprocess.PIPE, timeout=timeout, check=True)
    except (subprocess.CalledProcessError, subprocess.SubprocessError) as e:
        log.error(str(e))
        log.error("Failed to inspect image in registry!")
        return None
    except subprocess.TimeoutExpired as e:
        log.error(f"Image inspect timeout[{e.timeout}] expired!")
        log.error("Failed to inspect image in registry!")
        return None
    try:
        return json.loads(ret.stdout)
    except json.decoder.JSONDecodeError:
        log.error(f"Failed to decode image description!")


def copy_image_to_registry(src_scheme: str, image: str, registry: str, with_reference: str = None,
                           src_auth: str = None, dst_auth: str = None, insecure: bool = False,
                           timeout: int = None) -> subprocess.CompletedProcess | None:
    """

    :param src_scheme:
    :param image:
    :param registry:
    :param with_reference:
    :param src_auth:
    :param dst_auth:
    :param insecure:
    :param timeout:
    :return:
    """
    log.info(f"Copying {image} to {registry}...")
    cmd = ['skopeo', 'copy']
    if logging.getLogger().level < logging.INFO:
        cmd.append('--debug')
    if src_auth:
        cmd.append(f'--src-creds={src_auth}')  # username[:password]
    if dst_auth:
        cmd.append(f'--dest-creds={dst_auth}')  # username[:password]
    if insecure:
        cmd.append('--dest-tls-verify=false')
    if timeout:
        cmd.append(f"--command-timeout={timeout}")
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
    print(copy_image_to_registry(src_scheme='docker', image='gcr.io/google-containers/pause:latest',
                                 registry='registry.k3d.local:5000', with_reference='my-pause:latest',
                                 insecure=True, timeout=10))
    print(inspect_image(registry='gcr.io/google-containers', image='pause:latest', insecure=True, timeout=10))
