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

from app.ptx.connector import perform_pdc_data_exchange
from app.util.config import CONFIG, load_configuration, SKIPPED
from app.util.helper import get_resource_path, get_resource_scheme
from app.util.k8s import create_image_pull_secret
from app.util.parsers import DockerRegistryAuth
from app.util.skopeo import copy_image_to_registry, inspect_docker_image

log = logging.getLogger(__name__)


def collect_worker_image_from_repo(src: str, dst: str | None, src_auth: DockerRegistryAuth,
                                   retry: int = None, timeout: int = None) -> str | None:
    """

    :param src:
    :param dst:
    :param src_auth:
    :param retry:
    :param timeout:
    :return:
    """
    src_path = get_resource_path(src)
    img_name = get_resource_path(dst) if dst else src_path.rsplit('/', maxsplit=1)[-1]
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


def configure_worker_pull_credential(name: str, cred: DockerRegistryAuth, app: str, namespace: str = None,
                                     timeout: int = None) -> str | None:
    """

    :param name:
    :param cred:
    :param app:
    :param namespace:
    :param timeout:
    :return:
    """
    secret = create_image_pull_secret(name=name, user=cred.user, passwd=cred.secret, server=cred.server,
                                      namespace=namespace, app=app, projected=True, timeout=timeout)
    log.debug(f"Created secret description:\n{pprint.pformat(secret.to_dict()) if secret else None}")
    return secret.metadata.uid if secret else None


def collect_worker_from_ptx(contract_id: str, dst: str, retry: int = None, timeout: int = None) -> str | None:
    """

    :param contract_id:
    :param dst:
    :param retry:
    :param timeout:
    :return:
    """
    log.info(f"Acquiring worker resources based on contract[{contract_id}]...")
    data = perform_pdc_data_exchange(contract_id=contract_id, timeout=timeout)
    if data is None:
        log.error("Worker data exchange failed!")
        return None
    else:
        log.info(f"Worker data exchange was successful!")
    ##########################################################################################
    data_type, data_content = data['type'], data['content']
    log.info(f"Process received data as type: {data_type}")
    match data_type:
        case 'raw' | 'file':
            raise NotImplementedError
        case 'docker' | 'remote':
            docker_src, src_auth = data_content['image'], data_content.get('auth')
            docker_dst = data_content.get('dst', default=dst)
            src_insecure = src_auth.get('insecure', False) if src_auth else False
            result_id = collect_worker_image_from_repo(src=docker_src, dst=docker_dst,
                                                       src_auth=src_auth, src_insecure=src_insecure, src_ca_dir=None,
                                                       retry=retry, timeout=timeout)
        case 'auth' | 'secret':
            name = CONFIG.get('worker.pull-secret', data_content.get('worker.dst'))
            cred = data_content.get('credentials')
            app = CONFIG.get('worker.app', default='worker')
            result_id = configure_worker_pull_credential(name=name, cred=cred, app=app, timeout=timeout)
        case other:
            raise Exception(f"Unsupported data type: {other}")
    return result_id


########################################################################################################################

def get_worker_resources(data_path: str | pathlib.Path) -> str | None:
    """

    :param data_path:
    :return:
    """
    log.info("Obtaining worker configuration...")
    conn_timeout = int(CONFIG.get('connection.timeout', default=30))
    conn_retry = int(CONFIG.get('connection.retry', default=3))
    log.debug(f"Check worker setup in configuration...")
    worker_src = CONFIG.get('worker.src')
    if worker_src is None:
        log.warning("Worker source configuration is missing! Skipping...")
        CONFIG['worker.src'] = SKIPPED
    elif worker_src.upper() in ('INLINE', 'DATASOURCE'):
        log.debug(f"Trying to load worker configuration from {data_path}...")
        with open(data_path, 'r') as f:
            worker_cfg = json.load(f)
        load_configuration(base=worker_cfg['worker'])
    worker_src, worker_dst = CONFIG['worker.src'], CONFIG.get('worker.dst')
    log.debug(f"Worker setup is loaded from configuration: {worker_src = }, {worker_dst = }")
    result_id = None
    match get_resource_scheme(worker_src):
        case 'skip' | None:
            result_id = SKIPPED
        case 'git':
            raise NotImplementedError
        case 'docker' | 'remote':
            src_auth = DockerRegistryAuth.parse(CONFIG.get('worker.auth'))
            result_id = collect_worker_image_from_repo(src=worker_src, dst=worker_dst, src_auth=src_auth,
                                                       retry=conn_retry, timeout=conn_timeout)
        case 'auth' | 'secret':
            name, app = CONFIG.get('worker.pull-secret', default=worker_dst), CONFIG.get('worker.app', default='worker')
            cred = DockerRegistryAuth.parse(CONFIG.get('worker.auth'))
            result_id = configure_worker_pull_credential(name=name, cred=cred, app=app, timeout=conn_timeout)
        case 'ptx':
            result_id = collect_worker_from_ptx(contract_id=get_resource_path(worker_src), dst=worker_dst,
                                                retry=conn_retry, timeout=conn_timeout)
        case other:
            log.error(f"Unknown data source protocol: {other}")
            result_id = None
    return result_id
