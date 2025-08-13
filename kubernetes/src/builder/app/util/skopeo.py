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

log = logging.getLogger(__name__)


def __log_stderr(stderr: bytes):
    """

    :param stderr:
    :return:
    """
    for line in stderr.decode().splitlines():
        log.debug("[%s] - %s", *line.split(" ", maxsplit=2)[1:])


def get_direct_skopeo_command(op: str, mode: str, path: str = '', ref: str = '', on_behalf: str = None,
                              secret: str = None, insecure: bool = False, ca_dir: str = None,
                              retry: bool = None, timeout: int = None, verbose: bool = False) -> list[str]:
    """

    :param op:
    :param mode:
    :param path:
    :param ref:
    :param on_behalf:
    :param secret:
    :param insecure:
    :param ca_dir:
    :param retry:
    :param timeout:
    :param verbose:
    :return:
    """
    cmd = ['skopeo']
    if timeout:
        cmd.append(f'--command-timeout={timeout}s')
    if verbose:
        cmd.append(f'--debug')
    cmd.append(op)
    if on_behalf:
        if on_behalf == 'bearer':
            cmd.append(f"--registry-token={secret}")
        else:
            cmd.extend((f"--username={on_behalf}", f"--password={secret}"))
    cmd.append(f'--tls-verify={str(not insecure).lower()}')
    if ca_dir:
        cmd.append(f'--cert_dir={ca_dir}')
    if retry:
        cmd.append(f"--retry-times={retry}")
    cmd.append(f"{mode}{path}{'/' if path and ref else ''}{ref}")
    log.debug(f"Assembled command: {' '.join(cmd)}")
    return cmd


def get_bidirect_skopeo_command(op: str, src_mode: str, dst_mode: str,
                                src_path: str = '', src_ref: str = '', dst_path: str = '', dst_ref: str = '',
                                src_auth: tuple[str, str] = None, src_insecure: bool = False, src_ca_dir: str = None,
                                dst_auth: tuple[str, str] = None, dst_insecure: bool = False, dst_ca_dir: str = None,
                                retry: int = None, timeout: int = None, verbose: bool = False) -> list[str]:
    cmd = ['skopeo']
    if timeout:
        cmd.append(f"--command-timeout={timeout}s")
    if verbose:
        cmd.append(f'--debug')
    cmd.append(op)
    if src_auth:
        if src_auth[0] == 'bearer':
            cmd.append(f"--src-registry-token={src_auth[1]}")
        else:
            cmd.extend((f"--src-username={src_auth[0]}", f"--src-password={src_auth[1]}"))
    cmd.append(f'--src-tls-verify={str(not src_insecure).lower()}')
    if src_ca_dir:
        cmd.append(f'--src-cert_dir={src_ca_dir}')
    if dst_auth:
        if dst_auth[0] == 'bearer':
            cmd.append(f"--dest-registry-token={dst_auth[1]}")
        else:
            cmd.extend((f"--dest-username={dst_auth[0]}", f"--dest-password={dst_auth[1]}"))
    cmd.append(f'--dest-tls-verify={str(not dst_insecure).lower()}')
    if dst_ca_dir:
        cmd.append(f'--dest_cert_dir={dst_ca_dir}')
    if retry:
        cmd.append(f"--retry-times={retry}")
    cmd.extend((f"{src_mode}{src_path}{'/' if src_path and src_ref else ''}{src_ref}",
                f"{dst_mode}{dst_path}{'/' if dst_path and dst_ref else ''}{dst_ref}"))
    log.debug(f"Assembled command: {' '.join(cmd)}")
    return cmd


def inspect_docker_image(image: str, registry: str = 'docker.io', on_behalf: str = None, secret: str = None,
                         insecure: bool = False, retry: bool = None, timeout: int = None,
                         verbose: bool = False) -> dict | None:
    """

    :param registry:
    :param image:
    :param on_behalf:
    :param secret:
    :param insecure:
    :param retry:
    :param timeout:
    :param verbose:
    :return:
    """
    log.info(f"Validating {image} in {registry}...")
    cmd = get_direct_skopeo_command(op="inspect", mode="docker://", path=registry, ref=image,
                                    on_behalf=on_behalf, secret=secret, insecure=insecure,
                                    retry=retry, timeout=timeout, verbose=verbose)
    ret = None
    try:
        ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=True)
    except (subprocess.CalledProcessError, subprocess.SubprocessError) as e:
        __log_stderr(e.stderr)
        log.error(e)
    except subprocess.TimeoutExpired as e:
        log.error(f"Command timeout[{e.timeout}] expired!")
    if ret is None:
        log.error(f"Failed to inspect image[{image}] in registry[{registry}]!")
        return None
    elif verbose:
        __log_stderr(ret.stderr)
    try:
        return json.loads(ret.stdout)
    except json.decoder.JSONDecodeError:
        log.error(f"Failed to decode received image description!")


def delete_docker_image(image: str, registry: str, on_behalf: str = None, secret: str = None, insecure: bool = False,
                        retry: bool = None, timeout: int = None, verbose: bool = False) -> bool:
    """

    :param registry:
    :param image:
    :param on_behalf:
    :param secret:
    :param insecure:
    :param retry:
    :param timeout:
    :param verbose:
    :return:
    """
    log.info(f"Deleting {image} from {registry}...")
    cmd = get_direct_skopeo_command(op="delete", mode="docker://", path=registry, ref=image,
                                    on_behalf=on_behalf, secret=secret, insecure=insecure,
                                    retry=retry, timeout=timeout, verbose=verbose)
    ret = None
    try:
        ret = subprocess.run(cmd, stderr=subprocess.PIPE, timeout=timeout, check=True)
    except (subprocess.CalledProcessError, subprocess.SubprocessError) as e:
        __log_stderr(e.stderr)
        log.error(e)
    except subprocess.TimeoutExpired as e:
        log.error(f"Command timeout[{e.timeout}] expired!")
    if ret is None:
        log.error(f"Failed to delete image[{image}] from registry[{registry}]!")
        return False
    elif verbose:
        __log_stderr(ret.stderr)
    log.info(f"{image} is deleted from {registry} successfully!")
    return True


def copy_image_to_registry(image: str, registry: str, src_repo: str = '', with_reference: str = None,
                           src_auth: tuple[str, str] = None, src_insecure: bool = False, src_ca_dir: str = None,
                           dst_auth: tuple[str, str] = None, dst_insecure: bool = False, dst_ca_dir: str = None,
                           retry: int = None, timeout: int = None, verbose: bool = False) -> bool:
    """

    :param image:
    :param registry:
    :param src_repo:
    :param with_reference:
    :param src_auth:
    :param src_insecure:
    :param src_ca_dir:
    :param dst_auth:
    :param dst_insecure:
    :param dst_ca_dir:
    :param retry:
    :param timeout:
    :param verbose:
    :return:
    """
    src_mode = 'docker-archive:' if image.startswith('/') else 'docker://'
    log.info(f"Copying {image} into {registry}...")
    dst_ref = with_reference if with_reference is not None else image
    cmd = get_bidirect_skopeo_command(op="copy", src_mode=src_mode, src_path=src_repo, src_ref=image,
                                      dst_mode='docker://', dst_path=registry, dst_ref=dst_ref,
                                      src_auth=src_auth, src_insecure=src_insecure, src_ca_dir=src_ca_dir,
                                      dst_auth=dst_auth, dst_insecure=dst_insecure, dst_ca_dir=dst_ca_dir,
                                      retry=retry, timeout=timeout, verbose=verbose)
    ret = None
    try:
        ret = subprocess.run(cmd, stderr=subprocess.PIPE, timeout=timeout, check=True)
    except (subprocess.CalledProcessError, subprocess.SubprocessError) as e:
        __log_stderr(e.stderr)
        log.error(e)
    except subprocess.TimeoutExpired as e:
        log.error(f"Command timeout[{e.timeout}] expired!")
    if ret is None:
        log.error(f"Failed to copy {image} into {registry}!")
        return False
    elif verbose:
        __log_stderr(ret.stderr)
    log.info(f"{image} is copied into {registry} successfully!")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    # print(inspect_docker_image(image='alpine:latest', timeout=10, verbose=True))
    # print(inspect_docker_image(registry='gcr.io/google-containers', image='pause:latest', insecure=True, timeout=10,
    #                            verbose=True))
    print(copy_image_to_registry(image='gcr.io/google-containers/pause:latest', registry='registry.k3d.local:5000',
                                 with_reference='my-pause:latest', dst_auth=('demo', 'demo'), dst_insecure=True,
                                 timeout=10))
