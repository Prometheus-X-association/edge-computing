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
from app.util.skopeo import copy_image_to_registry, inspect_image

log = logging.getLogger(__package__)


def collect_worker_image_from_repo(src: str, dst: str, src_auth: dict = None, dst_auth: dict = None,
                                   with_ref: str = None, timeout: int = None) -> str | None:
    """

    :param src:
    :param dst:
    :param src_auth:
    :param dst_auth:
    :param with_ref:
    :param timeout:
    :return:
    """
    src_path, dst_path = get_resource_path(src), get_resource_path(dst)
    repo, img = dst_path.split('/', maxsplit=1)
    ref = with_ref if with_ref else img
    src_auth = DockerRegistryAuth.parse(src_auth).to_str() if src_auth else None
    dst_auth = DockerRegistryAuth.parse(dst_auth).to_str() if dst_auth else None
    ret = copy_image_to_registry(src_scheme='remote', image=src_path, registry=repo, with_reference=ref,
                                 src_auth=src_auth, dst_auth=dst_auth, insecure=True, timeout=timeout)
    if ret is None or ret.returncode != 0:
        return None
    image = inspect_image(registry=repo, image=src_path, insecure=True, timeout=timeout)
    log.debug(f"Created image description:\n{pprint.pformat(image)}")
    return image.get('Digest') if image else None


def configure_worker_credential(name: str, cred: dict, app: str, namespace: str = None,
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
    secret = create_image_pull_secret(name=name, user=cred.username, passwd=cred.password, namespace=namespace,
                                      app=app, projected=True, timeout=timeout)
    log.debug(f"Created secret description:\n{pprint.pformat(secret.to_dict()) if secret else None}")
    return secret.metadata.uid if secret else None


def collect_worker_from_ptx(contract_id: str, dst: str, timeout: int = None) -> str | None:
    """

    :param contract_id:
    :param dst:
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
            docker_dst, dst_auth = data_content.get('dst', dst), CONFIG.get('worker.auth.dst')
            result_id = collect_worker_image_from_repo(src=docker_src, dst=docker_dst,
                                                       src_auth=src_auth, dst_auth=dst_auth,
                                                       timeout=timeout)
        case 'auth' | 'secret':
            cred = data_content.get('credentials')
            app = CONFIG.get('worker.app', 'worker')
            secret_name = data_content.get('name', app)
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
    timeout = CONFIG.get('connection.timeout', 30)
    worker_src = CONFIG.get('worker.src')
    log.debug(f"Check worker setup in configuration...")
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
            src_auth, dst_auth = CONFIG.get('worker.auth.src'), CONFIG.get('worker.auth.dst')
            result_id = collect_worker_image_from_repo(src=worker_src, dst=worker_dst,
                                                       src_auth=src_auth, dst_auth=dst_auth,
                                                       timeout=timeout)
        case 'auth' | 'secret':
            secret_name = get_resource_path(worker_src)
            cred = CONFIG['worker.auth.src']
            app = CONFIG.get('worker.app', 'worker')
            result_id = configure_worker_credential(name=secret_name, cred=cred, app=app, timeout=timeout)
        case 'ptx':
            result_id = collect_worker_from_ptx(contract_id=get_resource_path(worker_src),
                                                dst=worker_dst,
                                                timeout=timeout)
        case other:
            log.error(f"Unknown data source protocol: {other}")
            result_id = None
    return result_id
