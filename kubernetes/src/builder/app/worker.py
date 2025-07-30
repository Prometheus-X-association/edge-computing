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

from app.util.helper import get_resource_path
from app.util.skopeo import copy_image_to_registry

log = logging.getLogger(__package__)


def collect_worker_image_from_repo(src: str, dst: str, auth: dict = None, with_ref: str = None,
                                   timeout: int = None) -> str:
    """

    :param src:
    :param dst:
    :param auth:
    :param with_ref:
    :param timeout:
    :return:
    """
    src_path, dst_path = get_resource_path(src), get_resource_path(dst)
    repo, img = dst_path.split('/', maxsplit=1)
    ref = with_ref if with_ref else img
    src_cred = f"{auth['username']}:{auth['password']}" if auth is not None else None
    ret = copy_image_to_registry(src_scheme='remote', image=src_path, registry=repo, with_reference=ref,
                                 src_auth=src_cred, insecure=True, timeout=timeout)
    return dst if ret.returncode == 0 else None


def configure_worker_credential(src: str, dst: str):
    pass


def collect_worker_from_ptx(contract_id: str, dst: str, timeout: int = None):
    pass
