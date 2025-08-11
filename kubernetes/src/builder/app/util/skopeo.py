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


def inspect_image(registry: str, image: str, on_behalf: str = None, secret: str = None, insecure: bool = False,
                  retry: bool = None, timeout: int = None) -> dict | None:
    """

    :param registry:
    :param image:
    :param on_behalf:
    :param secret:
    :param insecure:
    :param retry:
    :param timeout:
    :return:
    """
    log.info(f"Validating {image} in {registry}...")
    cmd = ['skopeo']
    if timeout:
        cmd.append(f'--command-timeout={timeout}s')
    cmd.append('inspect')
    if on_behalf:
        if on_behalf == 'bearer':
            cmd.append(f"--registry-token={secret}")
        else:
            cmd.extend((f"--username={on_behalf}", f"--password={secret}"))
    cmd.append(f'--tls-verify={str(not insecure).lower()}')
    if retry:
        cmd.append(f"--retry-times={retry}")
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
                           src_auth: tuple[str, str] = None, src_insecure: bool = False,
                           dst_auth: tuple[str, str] = None, dst_insecure: bool = False,
                           retry: int = None, timeout: int = None) -> subprocess.CompletedProcess | None:
    """

    :param src_scheme:
    :param image:
    :param registry:
    :param with_reference:
    :param src_auth:
    :param src_insecure:
    :param dst_auth:
    :param dst_insecure:
    :param retry:
    :param timeout:
    :return:
    """
    log.info(f"Copying {image} to {registry}...")
    cmd = ['skopeo']
    if timeout:
        cmd.append(f"--command-timeout={timeout}")
    cmd.append('copy')
    if logging.getLogger().level < logging.INFO:
        cmd.append('--debug')
    if src_auth:
        if src_auth[0] == 'bearer':
            cmd.append(f"--src-registry-token={src_auth[1]}")
        else:
            cmd.extend((f"--src-username={src_auth[0]}", f"--src-password={src_auth[1]}"))  # username[:password]
    cmd.append(f'--src-tls-verify={str(not src_insecure).lower()}')
    if dst_auth:
        if dst_auth[0] == 'bearer':
            cmd.append(f"--dst-registry-token={dst_auth[1]}")
        else:
            cmd.extend((f"--dst-username={dst_auth[0]}", f"--dst-password={dst_auth[1]}"))  # username[:password]
    cmd.append(f'--dst-tls-verify={str(not dst_insecure).lower()}')
    if retry:
        cmd.append(f"--retry-times={retry}")
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
                                 dst_insecure=True, timeout=10))
    print(inspect_image(registry='gcr.io/google-containers', image='pause:latest', insecure=True, timeout=10))
