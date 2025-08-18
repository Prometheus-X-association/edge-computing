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
import json
import logging
import pathlib
import pprint

from app.ptx.connector import perform_pdc_data_exchange
from app.util.config import CONFIG, load_configuration
from app.util.helper import get_resource_path, get_resource_scheme
from app.util.k8s import create_image_pull_secret
from app.util.parsers import DockerRegistryAuth
from app.util.skopeo import copy_image_to_registry, inspect_docker_image

log = logging.getLogger(__name__)


def collect_worker_image_from_repo(src: str, dst: str, with_ref: str = None,
                                   src_auth: dict | str = None, src_insecure: bool = False, src_ca_dir: str = None,
                                   retry: int = None, timeout: int = None) -> str | None:
    """

    :param src:
    :param dst:
    :param with_ref:
    :param src_auth:
    :param src_insecure:
    :param src_ca_dir:
    :param retry:
    :param timeout:
    :return:
    """
    src_path, dst_path = get_resource_path(src), get_resource_path(dst)
    repo, img = dst_path.split('/', maxsplit=1)
    ref = with_ref if with_ref else img
    if repo.lower() == "registry":
        repo = CONFIG.get('registry.url')
    dst_auth, dst_ca_dir = CONFIG.get('registry.auth.cred'), CONFIG.get('registry.auth.ca_dir')
    dst_insecure = CONFIG.get('registry.auth.insecure', False)
    src_auth = DockerRegistryAuth.parse(src_auth).to_tuple() if src_auth else None
    dst_auth = DockerRegistryAuth.parse(dst_auth).to_tuple() if dst_auth else None
    success = copy_image_to_registry(image=src_path, registry=repo, with_reference=ref,
                                     src_auth=src_auth, src_insecure=src_insecure, src_ca_dir=src_ca_dir,
                                     dst_auth=dst_auth, dst_insecure=dst_insecure, dst_ca_dir=dst_ca_dir,
                                     retry=retry, timeout=timeout, verbose=log.level < logging.INFO)
    if not success:
        return None
    image = inspect_docker_image(image=ref, registry=repo,
                                 on_behalf=dst_auth[0], secret=dst_auth[1], insecure=False, ca_dir=dst_ca_dir,
                                 retry=retry, timeout=timeout, verbose=log.level < logging.INFO)
    log.debug(f"Created image description:\n{pprint.pformat(image)}")
    return image.get('Digest') if image else None


def configure_worker_credential(name: str, cred: dict | str, app: str, namespace: str = None,
                                timeout: int = None) -> str | None:
    """

    :param name:
    :param cred:
    :param app:
    :param namespace:
    :param timeout:
    :return:
    """
    cred = DockerRegistryAuth.parse(cred)
    secret = create_image_pull_secret(name=name, user=cred.on_behalf, passwd=cred.secret, namespace=namespace,
                                      app=app, projected=True, timeout=timeout)
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
            docker_dst = data_content.get('dst', dst)
            src_insecure = src_auth.get('insecure', False) if src_auth else False
            result_id = collect_worker_image_from_repo(src=docker_src, dst=docker_dst,
                                                       src_auth=src_auth, src_insecure=src_insecure, src_ca_dir=None,
                                                       retry=retry, timeout=timeout)
        case 'auth' | 'secret':
            secret_name = data_content.get('name', CONFIG.get('registry.name', "registry"))
            cred = data_content.get('credentials')
            app = CONFIG.get('worker.app', 'worker')
            result_id = configure_worker_credential(name=secret_name, cred=cred, app=app, timeout=timeout)
        case other:
            raise Exception(f"Unsupported data type: {other}")
    return result_id


########################################################################################################################

def get_worker_resources(data_path: str | pathlib.Path) -> str:
    """

    :param data_path:
    :return:
    """
    log.info("Obtaining worker configuration...")
    conn_timeout, conn_retry = CONFIG.get('connection.timeout', 30), CONFIG.get('connection.retry', 3)
    log.debug(f"Check worker setup in configuration...")
    worker_src = CONFIG.get('worker.src')
    if worker_src is None or worker_src.lower() in ('inline', 'datasource'):
        log.debug(f"Trying to load worker configuration from {data_path}...")
        with open(data_path, 'r') as f:
            worker_cfg = json.load(f)
        load_configuration(base=worker_cfg['worker'])
    worker_src, worker_dst = CONFIG['worker.src'], CONFIG['worker.dst']
    log.debug(f"Worker setup is loaded from configuration: {worker_src = }, {worker_dst = }")
    match get_resource_scheme(worker_src):
        case 'git':
            raise NotImplementedError
        case 'docker' | 'remote':
            src_auth = CONFIG.get('worker.auth.cred')
            src_insecure = CONFIG.get('worker.auth.insecure', False)
            ca_dir = CONFIG.get('worker.auth.ca_dir')
            result_id = collect_worker_image_from_repo(src=worker_src, dst=worker_dst,
                                                       src_auth=src_auth, src_insecure=src_insecure, src_ca_dir=ca_dir,
                                                       retry=conn_retry, timeout=conn_timeout)
        case 'auth' | 'secret':
            src_path = get_resource_path(worker_src)
            if ':' in src_path:
                secret_name, cred = CONFIG.get('registry.name', "registry"), src_path
            else:
                secret_name, cred = src_path, CONFIG.get('worker.auth.cred')
            app = CONFIG.get('worker.app', 'worker')
            result_id = configure_worker_credential(name=secret_name, cred=cred, app=app, timeout=conn_timeout)
        case 'ptx':
            result_id = collect_worker_from_ptx(contract_id=get_resource_path(worker_src), dst=worker_dst,
                                                retry=conn_retry, timeout=conn_timeout)
        case other:
            log.error(f"Unknown data source protocol: {other}")
            result_id = None
    return result_id
