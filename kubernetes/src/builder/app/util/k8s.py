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
import base64
import json
import logging
import pathlib

from kubernetes import config, client
from kubernetes.client import OpenApiException
from kubernetes.config import ConfigException
from kubernetes.config.incluster_config import InClusterConfigLoader

log = logging.getLogger(__package__)


def _load_incluster_projected_config(token: str, cert: str, client_configuration: client.Configuration = None,
                                     try_refresh_token: bool = True) -> InClusterConfigLoader:
    """

    :param token:
    :param cert:
    :param client_configuration:
    :param try_refresh_token:
    :return:
    """
    return InClusterConfigLoader(token_filename=token, cert_filename=cert,
                                 try_refresh_token=try_refresh_token).load_and_set(client_configuration)


##########################################################################################

def check_kube_api_cfg():
    print("  Check automount serviceaccount config  ".center(60, "="))
    try:
        config.load_incluster_config()
        print(client.VersionApi().get_code())
    except ConfigException as e:
        print(f"Error: {e}")


def check_projected_kube_api_cfg(projected_dir: str = '/var/run/secrets/projected'):
    print("  Check projected serviceaccount config  ".center(60, '='))
    try:
        _load_incluster_projected_config(token=projected_dir + '/token',
                                         cert=projected_dir + '/ca.crt')
        print(client.VersionApi().get_code())
    except ConfigException as e:
        print(f"Error: {e}")


##########################################################################################

PROJECTED_TOKEN_FILE = "/var/run/secrets/projected/token"
PROJECTED_CERT_FILE = "/var/run/secrets/projected/ca.crt"
PROJECTED_NS_FILE = "/var/run/secrets/projected/namespace"


def create_image_pull_secret(name: str, user: str, passwd: str, email: str = "", namespace: str = None,
                             app: str = None, projected: bool = False) -> client.V1Secret | None:
    """
        E.g.:
    >>> create_image_pull_secret(name="test-pull-sec", user='test-user', passwd='pass1234',
    >>>                               namespace='ptx-edge', app='builder', projected=True)

    :param name:
    :param user:
    :param passwd:
    :param email:
    :param namespace:
    :param app:
    :param projected:
    :return:
    """
    log.info("Creating image pull secret...")
    log.debug(f"Loading K8s configuration...")
    if projected:
        _load_incluster_projected_config(token=PROJECTED_TOKEN_FILE, cert=PROJECTED_CERT_FILE)
    else:
        config.load_incluster_config()
    b64_auth = base64.b64encode(f"{user}:{passwd}".encode("utf-8")).decode("utf-8")
    docker_cfg = dict(auths=dict(registry=dict(username=user, password=passwd, auth=b64_auth, email=email)))
    b64_docker_cfg = base64.b64encode(json.dumps(docker_cfg).encode("utf-8")).decode("utf-8")
    secret_body = client.V1Secret(metadata=client.V1ObjectMeta(name=name,
                                                               labels={"app": app} if app else None),
                                  type="kubernetes.io/dockerconfigjson",
                                  data={'.dockerconfigjson': b64_docker_cfg})
    if namespace is None:
        namespace = pathlib.Path(PROJECTED_NS_FILE).read_text() if projected else "default"
    try:
        return client.CoreV1Api().create_namespaced_secret(namespace=namespace, body=secret_body)
    except OpenApiException as e:
        log.error(f"Error: {e}")


def create_service():
    ...


def create_endpoint():
    ...


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    ###
    check_kube_api_cfg()
    check_projected_kube_api_cfg()
    ###
    ret = create_image_pull_secret(name="test-pull-sec", user='test-user', passwd='pass1234', namespace='ptx-edge',
                                   app='builder', projected=True)
    print(ret)
