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
import json
import logging
import pathlib
import pprint
import typing

from app.ptx.connector import perform_pdc_consumer_exchange
from app.util.config import CONFIG, load_configuration, SKIPPED
from app.util.helper import get_resource_path, get_resource_scheme_from_uri
from app.util.k8s import create_image_pull_secret
from app.util.parsers import DockerRegistryAuth
from app.util.skopeo import copy_image_to_registry, inspect_docker_image

log = logging.getLogger(__name__)


def collect_worker_image_from_repo(src: str, dst: str | None, src_auth: DockerRegistryAuth,
                                   retry: int | None = None, timeout: int | None = None) -> str | None:
    """

    :param src:
    :param dst:
    :param src_auth:
    :param retry:
    :param timeout:
    :return:
    """
    if (src_path := get_resource_path(src)) is None:
        return None
    img_name = get_resource_path(dst) if dst else src_path.rsplit('/', maxsplit=1)[-1]
    if img_name is None:
        return None
    dst_auth = DockerRegistryAuth.parse(CONFIG['registry.auth'])
    success = copy_image_to_registry(
        image=src_path, registry=dst_auth.server, with_reference=img_name,
        src_auth=src_auth.get_creds(), src_insecure=src_auth.insecure, src_ca_dir=src_auth.ca_dir,
        dst_auth=dst_auth.get_creds(), dst_insecure=dst_auth.insecure, dst_ca_dir=dst_auth.ca_dir,
        retry=retry, timeout=timeout, verbose=log.level < logging.INFO)
    if not success:
        return None
    image = inspect_docker_image(
        image=img_name, registry=dst_auth.server,
        on_behalf=dst_auth.user, secret=dst_auth.secret, insecure=dst_auth.insecure, ca_dir=dst_auth.ca_dir,
        retry=retry, timeout=timeout, verbose=log.level < logging.INFO)
    log.debug(f"Created image description:\n{pprint.pformat(image)}")
    return image.get('Digest') if image else None


def configure_worker_pull_credential(name: str, cred: DockerRegistryAuth, app: str, namespace: str | None = None,
                                     timeout: int | None = None) -> str | None:
    """

    :param name:
    :param cred:
    :param app:
    :param namespace:
    :param timeout:
    :return:
    """
    user, secret = cred.get_creds()
    if user is None or secret is None:
        log.error("Undefined worker pull credentials!")
        return None
    secret = create_image_pull_secret(name=name, user=user, passwd=secret, server=cred.server,
                                      namespace=namespace, app=app, projected=True, timeout=timeout)
    log.debug(f"Created secret description:\n{pprint.pformat(secret.to_dict()) if secret else None}")
    return secret.metadata.uid if secret else None


def collect_worker_from_ptx(exchange: str, dst: str, retry: int | None = None,
                            timeout: int | None = None) -> str | None:
    """

    :param exchange:
    :param dst:
    :param retry:
    :param timeout:
    :return:
    """
    log.info(f"Acquiring worker resources based on contract[{exchange}]...")
    data = perform_pdc_consumer_exchange(exchange=exchange, timeout=timeout)
    # {
    #     "type": ...,
    #     "content": {
    #         "image": ...,
    #         "auth": {
    #             "server": ...,
    #             "user": ...,
    #             "secret": ...,
    #             "insecure": ...,
    #             "ca_dir": ...
    #          },
    #        "dst": ...
    #     }
    # }
    if data is None:
        log.error("Worker data exchange failed!")
        return None
    else:
        log.info(f"Worker data exchange was successful!")
    ##########################################################################################
    data_type, data_content = str(data['type']), data['content']
    log.info(f"Process received data as type: {data_type}")
    result_id = None
    match data_type.upper():
        case 'RAW' | 'FILE':
            raise NotImplementedError
        case 'DOCKER' | 'REMOTE':
            docker_src, docker_dst = data_content['image'], data_content.get('dst', default=dst)
            src_auth = DockerRegistryAuth.parse(data_content.get('auth'))
            result_id = collect_worker_image_from_repo(src=docker_src, dst=docker_dst, src_auth=src_auth,
                                                       retry=retry, timeout=timeout)
        case 'SECRET' | 'AUTH':
            name = CONFIG.get('worker.pull-secret', data_content.get('worker.dst'))
            cred = DockerRegistryAuth.parse(data_content.get('auth'))
            app = CONFIG.get('worker.app', default='worker')
            result_id = configure_worker_pull_credential(name=name, cred=cred, app=app, timeout=timeout)
        case other:
            raise Exception(f"Unsupported data type: {other}")
    return result_id


########################################################################################################################

def get_worker_resources(data_path: str | pathlib.Path | dict[str, typing.Any]) -> str | None:
    """

    :param data_path:
    :return:
    """
    log.info("Obtaining worker configuration...")
    conn_timeout = int(CONFIG.get('connection.timeout', default=30))
    conn_retry = int(CONFIG.get('connection.retry', default=3))
    log.debug(f"Check worker setup in configuration...")
    if (worker_method := CONFIG.get('worker.method')) is None:
        worker_method = get_resource_scheme_from_uri(CONFIG.get('worker.src'))
    if worker_method is None:
        log.error("Undefined worker collection method!")
        return None
    elif worker_method.upper() in ('INLINE', 'DATASOURCE'):
        log.debug(f"Trying to load worker configuration from {data_path}...")
        if isinstance(data_path, (pathlib.Path, str)):
            try:
                with open(data_path, 'r') as f:
                    worker_cfg = json.load(f).get('worker')
            except:
                log.error(f"Failed to load worker configuration from {data_path}!")
                worker_cfg = None
        elif isinstance(data_path, dict):
            worker_cfg = data_path.get('content', {}).get('worker')
        load_configuration(base=worker_cfg)
    elif not CONFIG.get('worker.src'):
        log.warning("Worker source configuration is missing! Set collection skipping...")
        worker_method = 'SKIP'
    worker_src, worker_dst = CONFIG['worker.src'], CONFIG.get('worker.dst')
    log.debug(f"Worker setup is loaded from configuration: {worker_src = }, {worker_dst = }")
    result_id = None
    match worker_method.upper():
        case 'SKIP' | None:
            log.warning("Worker collection is skipped!")
            result_id = SKIPPED
        case 'DOCKER' | 'REMOTE':
            src_auth = DockerRegistryAuth.parse(CONFIG.get('worker.auth'))
            result_id = collect_worker_image_from_repo(src=worker_src, dst=worker_dst, src_auth=src_auth,
                                                       retry=conn_retry, timeout=conn_timeout)
        case 'AUTH' | 'SECRET':
            name, app = CONFIG.get('worker.pull-secret', default=worker_dst), CONFIG.get('worker.app', default='worker')
            cred = DockerRegistryAuth.parse(CONFIG.get('worker.auth'))
            result_id = configure_worker_pull_credential(name=name, cred=cred, app=app, timeout=conn_timeout)
        case 'PTX':
            if (exchange := get_resource_path(worker_src)) is not None:
                result_id = collect_worker_from_ptx(exchange=exchange, dst=worker_dst,
                                                    retry=conn_retry, timeout=conn_timeout)
        case 'GIT':
            raise NotImplementedError
        case other:
            log.error(f"Unknown worker method: {other}")
            result_id = None
    return result_id
