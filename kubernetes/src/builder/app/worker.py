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
import logging
import pprint

from app.util.helper import get_resource_path
from app.util.k8s import create_image_pull_secret
from app.util.skopeo import copy_image_to_registry, inspect_image

log = logging.getLogger(__package__)


def collect_worker_image_from_repo(src: str, dst: str, src_auth: tuple[str, str] = None,
                                   dst_auth: tuple[str, str] = None, with_ref: str = None,
                                   timeout: int = None) -> str | None:
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
    ret = copy_image_to_registry(src_scheme='remote', image=src_path, registry=repo, with_reference=ref,
                                 src_auth=src_auth, dst_auth=dst_auth, insecure=True, timeout=timeout)
    if ret.returncode != 0:
        return None
    image = inspect_image(registry=repo, image=src_path, insecure=True, timeout=timeout)
    log.debug(f"Created image description:\n{pprint.pformat(image)}")
    return image.get('Digest') if image else None


def configure_worker_credential(name: str, cred: tuple[str, str], app: str, namespace: str = None) -> str | None:
    """

    :param name:
    :param cred:
    :param app:
    :param namespace:
    :return:
    """
    secret = create_image_pull_secret(name=name, user=cred[0], passwd=cred[1], namespace=namespace, app=app,
                                      projected=True)
    log.debug(f"Created secret description:\n{pprint.pformat(secret.to_dict()) if secret else None}")
    return secret.metadata.uid if secret else None


def collect_worker_from_ptx(contract_id: str, dst: str, timeout: int = None):
    pass
