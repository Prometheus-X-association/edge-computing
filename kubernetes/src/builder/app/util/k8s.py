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
import base64
import functools
import json
import logging
import pathlib
import threading
import time
import typing
from types import TracebackType

from kubernetes import config, client
from kubernetes.client import OpenApiException
from kubernetes.config import ConfigException
from kubernetes.config.incluster_config import InClusterConfigLoader
from kubernetes.leaderelection import electionconfig, leaderelection

try:
    from kubernetes.leaderelection.resourcelock.leaselock import LeaseLock as LeaderElectionLock
except ImportError:
    from kubernetes.leaderelection.resourcelock.configmaplock import ConfigMapLock as LeaderElectionLock

from app.util.helper import deep_filter

log = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def _load_incluster_projected_config(token: str,
                                     cert: str,
                                     client_configuration: client.Configuration | None = None,
                                     try_refresh_token: bool = True) -> InClusterConfigLoader:
    """

    :param token:
    :param cert:
    :param client_configuration:
    :param try_refresh_token:
    :return:
    """
    return InClusterConfigLoader(token_filename=token,
                                 cert_filename=cert,
                                 try_refresh_token=try_refresh_token).load_and_set(client_configuration)


##########################################################################################

def check_kube_api_cfg():
    print("  Check automount serviceaccount config  ".center(60, "="))
    try:
        config.load_incluster_config()
        print("Received response:\n", client.VersionApi().get_code())
    except ConfigException as e:
        print(f"Error: {e}")


def check_projected_kube_api_cfg(projected_dir: str = '/var/run/secrets/projected'):
    print("  Check projected serviceaccount config  ".center(60, '='))
    try:
        _load_incluster_projected_config(token=projected_dir + '/token',
                                         cert=projected_dir + '/ca.crt')
        print("Received response:\n", client.VersionApi().get_code())
    except ConfigException as e:
        print(f"Error: {e}")


##########################################################################################

PROJECTED_TOKEN_FILE = "/var/run/secrets/projected/token"
PROJECTED_CERT_FILE = "/var/run/secrets/projected/ca.crt"
PROJECTED_NS_FILE = "/var/run/secrets/projected/namespace"


def create_image_pull_secret(name: str, user: str, passwd: str, server: str = "https://index.docker.io/v1/",
                             namespace: str | None = None, app: str | None = None, projected: bool = True,
                             timeout: int | None = None) -> client.V1Secret | None:
    """

    :param name:
    :param user:
    :param passwd:
    :param server:
    :param namespace:
    :param app:
    :param projected:
    :param timeout:
    :return:
    """
    log.info("Creating image pull secret...")
    log.debug(f"Loading K8s configuration...")
    if projected:
        _load_incluster_projected_config(token=PROJECTED_TOKEN_FILE, cert=PROJECTED_CERT_FILE)
    else:
        config.load_incluster_config()
    b64_auth = base64.b64encode(f"{user}:{passwd}".encode("utf-8")).decode("utf-8")
    docker_cfg = {'auths': {server: {'auth': b64_auth}}}
    b64_docker_cfg = base64.b64encode(json.dumps(docker_cfg).encode("utf-8")).decode("utf-8")
    secret_body = client.V1Secret(metadata=client.V1ObjectMeta(name=name,
                                                               labels={"app": app} if app else None),
                                  type="kubernetes.io/dockerconfigjson",
                                  data={'.dockerconfigjson': b64_docker_cfg})
    log.debug(f"Created secret body:\n{json.dumps(deep_filter(secret_body.to_dict()), indent=4, default=str)}")
    if namespace is None:
        namespace = pathlib.Path(PROJECTED_NS_FILE).read_text() if projected else "default"
    try:
        return client.CoreV1Api().create_namespaced_secret(namespace=namespace,
                                                           body=secret_body,
                                                           _request_timeout=timeout)
    except OpenApiException as e:
        log.error(f"Error:\n{e}")


def create_service(name: str, port: int, target_port: int, namespace: str | None = None,
                   selector: dict[str, str] | None = None, stype: str = "ClusterIP", app: str | None = None,
                   projected: bool = True, timeout: int | None = None) -> client.V1Service | None:
    """

    :param name:
    :param port:
    :param target_port:
    :param namespace:
    :param selector:
    :param app:
    :param stype:
    :param projected:
    :param timeout:
    :return:
    """
    log.info("Creating service...")
    log.debug(f"Loading K8s configuration...")
    if projected:
        _load_incluster_projected_config(token=PROJECTED_TOKEN_FILE, cert=PROJECTED_CERT_FILE)
    else:
        config.load_incluster_config()
    service_body = client.V1Service(metadata=client.V1ObjectMeta(name=name,
                                                                 labels={"app": app} if app else None),
                                    spec=client.V1ServiceSpec(type=stype,
                                                              selector=selector,
                                                              ports=[client.V1ServicePort(name="pdc-port",
                                                                                          protocol="TCP",
                                                                                          port=port,
                                                                                          target_port=target_port)]))
    log.debug(f"Created service body:\n{json.dumps(deep_filter(service_body.to_dict()), indent=4, default=str)}")
    if namespace is None:
        namespace = pathlib.Path(PROJECTED_NS_FILE).read_text() if projected else "default"
    try:
        return client.CoreV1Api().create_namespaced_service(namespace=namespace,
                                                            body=service_body,
                                                            _request_timeout=timeout)
    except OpenApiException as e:
        log.error(f"Error:\n{e}")


def create_endpointslice(service_name: str, address: str, target_port: int, namespace: str | None = None,
                         app: str | None = None, projected: bool = True,
                         timeout: int | None = None) -> client.V1EndpointSlice | None:
    """

    :param service_name:
    :param address:
    :param target_port:
    :param namespace:
    :param app:
    :param projected:
    :param timeout:
    :return:
    """
    log.info("Creating endpointslice...")
    log.debug(f"Loading K8s configuration...")
    if projected:
        _load_incluster_projected_config(token=PROJECTED_TOKEN_FILE, cert=PROJECTED_CERT_FILE)
    else:
        config.load_incluster_config()
    labels = {"kubernetes.io/service-name": service_name,
              "endpointslice.kubernetes.io/managed-by": "controller.pdc.ptx-edge.org"}
    if app:
        labels["app"] = app
    endpointslice_body = client.V1EndpointSlice(metadata=client.V1ObjectMeta(name=service_name,
                                                                             labels=labels),
                                                address_type="IPv4",
                                                ports=[client.DiscoveryV1EndpointPort(name="pdc-port",
                                                                                      app_protocol="http",
                                                                                      protocol="TCP",
                                                                                      port=target_port)],
                                                endpoints=[client.V1Endpoint(addresses=[address])])
    log.debug(
        f"Created endpointslice body:\n{json.dumps(deep_filter(endpointslice_body.to_dict()), indent=4, default=str)}")
    if namespace is None:
        namespace = pathlib.Path(PROJECTED_NS_FILE).read_text() if projected else "default"
    try:
        return client.DiscoveryV1Api().create_namespaced_endpoint_slice(namespace=namespace,
                                                                        body=endpointslice_body,
                                                                        _request_timeout=timeout)
    except OpenApiException as e:
        log.error(f"Error:\n{e}")


class K8sLeaderElectorManager(object):
    """Manager object to govern K8s leader elector and wait for successful synced task execution"""
    PROJECTED_DIR = "/var/run/secrets/projected/"
    TOKEN_FILE = PROJECTED_DIR + "token"
    CERT_FILE = PROJECTED_DIR + "ca.crt"
    NS_FILE = PROJECTED_DIR + "namespace"

    def __init__(self, lock_name: str, identity: str, timeout: int, namespace: str | None = None,
                 projected: bool = True, retry: int = 10):
        self._timeout = timeout
        self.init_client(projected)
        if not namespace:
            namespace = pathlib.Path(self.NS_FILE).read_text() if projected else "default"
        self.elector = leaderelection.LeaderElection(
            electionconfig.Config(
                LeaderElectionLock(name=lock_name,
                                   namespace=namespace,
                                   identity=identity),
                lease_duration=self._timeout,
                renew_deadline=round(0.75 * self._timeout),
                retry_period=max(min(self._timeout // 2, retry), 3),
                onstarted_leading=self._on_start_handler,
                onstopped_leading=self._on_stopped_handler))
        self._runner = threading.Thread(target=self._execute_elector,
                                        name=f"{lock_name}-{identity}",
                                        daemon=True)
        self._task: functools.partial | None = None
        self._executed = threading.Event()
        self.__leader = False
        self.__result: typing.Any = None

    @classmethod
    def init_client(cls, projected: bool, token: str = TOKEN_FILE, cert: str = CERT_FILE):
        """Load K8s in-cluster config from default or a projected path."""
        if projected:
            log.info(f"Loading projected K8s client configuration...")
            InClusterConfigLoader(token_filename=token,
                                  cert_filename=cert,
                                  try_refresh_token=True).load_and_set()
        else:
            log.info(f"Loading in-cluster K8s client configuration...")
            config.load_incluster_config()

    @property
    def executed(self) -> bool:
        return self._executed.is_set()

    @property
    def leader(self) -> bool:
        return self.__leader

    def with_task(self, task: typing.Callable | None = None, *args, **kwargs) -> K8sLeaderElectorManager:
        """Helper function to define task inline with context manager definition."""
        self._task = functools.partial(task, *args, **kwargs) if task else None
        return self

    def with_augmented_task(self, task: typing.Callable | None = None, *args, **kwargs) -> K8sLeaderElectorManager:
        """Helper function to define task inline with context manager definition."""
        self._task = functools.partial(task, self, *args, **kwargs) if task else None
        return self

    def _on_start_handler(self):
        """Execute task and set waited event."""
        self.__leader = True
        if self._task:
            log.debug(f"Calling task[{self._task.func.__name__}]...")
            try:
                self.__result = self._task()
                log.debug(f"Task[{self._task.func.__name__}] finished!")
            except Exception as e:
                log.exception(e)
        else:
            log.warning(f"No executable task is defined!")
        self._executed.set()

    def _on_stopped_handler(self):
        log.debug(f"Lease time ended!")
        self.__leader = False

    def _execute_elector(self):
        """Start executor and wait for exit exception."""
        log.info("Leader elector started!")
        try:
            self.elector.run()
        except AttributeError as e:
            # Hackish solution to stop elector loop by raising an exception manually
            if 'lock' not in e.name:
                log.exception(e)
        self.__leader = False
        log.info(f"Leader elector finished!")

    def start(self, task: typing.Callable | None = None, *args, **kwargs) -> K8sLeaderElectorManager:
        """Start executor in separate thread."""
        if not self._runner.is_alive():
            if not self._task and task:
                self.with_task(task, *args, **kwargs)
            self._runner.start()
        else:
            log.error(f"Leader elector already started!")
        return self

    def wait(self) -> typing.Any:
        """Blocking wait for allocated lock and finished task."""
        if not self._executed.wait(timeout=self._timeout + 1):
            log.error(f"Wait timeout[{self._timeout}] reached!")
        return self.__result if self._executed.is_set() else None

    def release(self, lock) -> bool:
        """Release lease lock."""
        if self.__leader:
            log.warning(f"Elector is still the leader while lock is being released!")
        found, lock_record = lock.get(lock.name, lock.namespace)
        if not found:
            log.error(f"Lock[{lock.name}] not found!")
            return False
        elif lock_record.holder_identity != lock.identity:
            log.warning(f"Lock[{lock.name}] already transitioned!")
            return True
        else:
            lock_record.holder_identity = ""
            return lock.update(lock.name, lock.namespace, lock_record)

    def stop(self, blocking: bool = True):
        """Stop executor by force-raising an exception."""
        log.debug(f"Stopping leader elector...")
        _lock = self.elector.election_config.lock
        self.elector.election_config = None  # Cause exception when runner thread tries to access config
        if blocking:
            self._runner.join(timeout=self._timeout)
        self._executed.clear()
        log.debug(f"Releasing lock[{_lock.name}]...")
        if self.release(_lock):
            log.debug("Lock is released!")
        else:
            log.error("Lock release failed!")

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc_val: BaseException | None,
                 exc_tb: TracebackType | None):
        self.stop()


def test_threaded_leader_elector():
    InClusterConfigLoader(token_filename=PROJECTED_TOKEN_FILE,
                          cert_filename=PROJECTED_CERT_FILE,
                          try_refresh_token=True).load_and_set()
    lock = LeaderElectionLock(name="ptx-pdc-lock", namespace="ptx-edge", identity="xyz")
    config = electionconfig.Config(lock, lease_duration=20, renew_deadline=15, retry_period=5,
                                   onstarted_leading=lambda: time.sleep(10), onstopped_leading=None)
    elector = leaderelection.LeaderElection(config)
    t = threading.Thread(target=elector.run, daemon=True)
    t.start()
    print("leaderelection started...")
    time.sleep(10)
    print("leaderelection stopping...")
    elector.election_config = None
    print("leaderelection waited...")
    t.join()


def test_elector_manager():
    mgr = K8sLeaderElectorManager(lock_name="ptx-pdc-lock",
                                  identity="xxx",
                                  timeout=20,
                                  retry=5).with_task(lambda _, c, v: time.sleep(10))
    mgr.start()
    result = mgr.wait()
    mgr.stop()


def test_elector_context_manager():
    mgr = K8sLeaderElectorManager(lock_name="ptx-pdc-lock",
                                  identity="xxx",
                                  timeout=20,
                                  retry=5)
    with mgr.with_task(lambda _, c, v: time.sleep(10)) as mgr:
        result = mgr.wait()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    ###
    # check_kube_api_cfg()
    # check_projected_kube_api_cfg()
    test_threaded_leader_elector()
    test_elector_manager()
    test_elector_context_manager()
