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
import argparse
import json
import logging
import os
import pathlib
import sys
import typing

from kubernetes import client
from kubernetes.client import OpenApiException, ApiException
from kubernetes.config import ConfigException
from kubernetes.config.incluster_config import InClusterConfigLoader

log = logging.getLogger(__name__)

PROJECTED_TOKEN_FILE = "/var/run/secrets/projected/token"
PROJECTED_CERT_FILE = "/var/run/secrets/projected/ca.crt"
PROJECTED_NS_FILE = "/var/run/secrets/projected/namespace"

LABEL_K8S_ENDPOINTSLICE_SRV_NAME = 'kubernetes.io/service-name'
LABEL_K8S_ENDPOINTSLICE_MGR = 'endpointslice.kubernetes.io/managed-by'

LABEL_PTX_CONNECTOR = 'connector.dataspace.ptx.org'
LABEL_PTX_CONNECTOR_ENABLED = f'{LABEL_PTX_CONNECTOR}/enabled'
LABEL_PTX_PRIVACY_ZONE = 'privacy-zone.dataspace.ptx.org'

DEF_PDC_PORT = 3000
DEF_PDC_NODEPORT = 30003
DEF_NS = "ptx-edge"
DEF_APP = "pdc"
DEF_PORT_NAME = "pdc-port"
DEF_ZONE_ID = "zone-0"

CONFIG = {"port": int(os.getenv("PDC_PORT", default=DEF_PDC_PORT)),
          "pod": os.getenv("HOSTNAME"),
          "ip": os.getenv("NODE_IP"),
          "node": os.getenv("NODE_NAME"),
          "namespace": os.getenv("NAMESPACE", default=DEF_NS),
          "def_zone": os.getenv("DEF_ZONE", default=DEF_ZONE_ID),
          "app": os.getenv("APP_NAME", default=DEF_APP)}

REQUIRED_FIELDS = ("type", "namespace")


########################################################################################################################

def dump_k8s_obj(o: dict) -> str:
    def _deep_filter(data: object, keep: typing.Callable = bool) -> object:
        """

        :param data:
        :param keep:
        :return:
        """
        if isinstance(data, dict):
            return dict(filter(lambda kv: bool(kv[1]), ((k, _deep_filter(v, keep)) for k, v in data.items())))
        elif isinstance(data, (list, tuple, set)):
            return type(data)(filter(bool, (_deep_filter(v, keep) for v in data)))
        elif keep(data):
            return data
        else:
            return None

    return json.dumps(_deep_filter(o), indent=4, default=str)


def _load_config(token: str = PROJECTED_TOKEN_FILE, cert: str = PROJECTED_CERT_FILE) -> InClusterConfigLoader:
    """
    
    :param token: 
    :param cert: 
    :return: 
    """
    log.debug(f"Loading K8s configuration...")
    try:
        return InClusterConfigLoader(token_filename=token, cert_filename=cert).load_and_set()
    except ConfigException as e:
        print(f"Config error:\n{e}")
        sys.exit(os.EX_CONFIG)


def _collect_privacy_zone_labels(node: str = None, ip: str = None) -> list[str | None]:
    """

    :param node:
    :param ip:
    :return:
    """
    log.info(f">>> Collect Privacy Zone labels...")
    if node is not None:
        v1_node_list = client.CoreV1Api().list_node(field_selector=f'metadata.name={node}',
                                                    label_selector=f'{LABEL_PTX_CONNECTOR_ENABLED}=true')
        if len(v1_node_list.items) < 1:
            log.error(f"Node: {node} not found!")
            return []
        node_obj: client.V1Node = v1_node_list.items[0]
    elif ip is not None:
        v1_node_list = client.CoreV1Api().list_node(label_selector=f'{LABEL_PTX_CONNECTOR_ENABLED}=true')
        log.debug(f"Received nodes:\n{dump_k8s_obj(v1_node_list.to_dict())}")
        node_obj: client.V1Node = [n for n in v1_node_list.items if
                                   list(filter(lambda a: a.type == 'InternalIP' and a.address == ip,
                                               n.status.addresses))][0]
    else:
        log.error(f"Node[name: {node}, ip: {ip}] not found!")
        return []
    log.debug(f"Received node object: {json.dumps(node_obj.to_dict(), indent=4, default=str)}")
    labels = [l for l, v in node_obj.metadata.labels.items() if l.startswith(LABEL_PTX_PRIVACY_ZONE) and v == 'true']
    log.info(f"Extracted privacy zone labels: {labels}")
    return labels


def _delete_service(name: str, namespace: str) -> client.V1Service:
    log.debug(f">>> Delete service[{name}]...")
    return client.CoreV1Api().delete_namespaced_service(name=name, namespace=namespace)


def _delete_endpointslice(name: str, namespace: str, ) -> client.V1Status:
    log.debug(f">>> Delete endpointslice[{name}]...")
    return client.DiscoveryV1Api().delete_namespaced_endpoint_slice(name=name, namespace=namespace)


def _create_headless_service(name: str, port: int, namespace: str, app: str = None) -> client.V1Service:
    """

    :param name:
    :param port:
    :param namespace:
    :param app:
    :return:
    """
    log.info(f">>> Creating headless service with name: {name}")
    srv_body = client.V1Service(metadata=client.V1ObjectMeta(name=name,
                                                             labels={"app": app} if app else None),
                                spec=client.V1ServiceSpec(type="ClusterIP",
                                                          cluster_ip="None",

                                                          ports=[client.V1ServicePort(name=DEF_PORT_NAME,
                                                                                      protocol="TCP",
                                                                                      port=port,
                                                                                      target_port=port)]))
    return client.CoreV1Api().create_namespaced_service(namespace=namespace, body=srv_body)


def _create_cluster_service(name: str, port: int, namespace: str, selector: dict[str, str],
                            app: str = None) -> client.V1Service:
    """

    :param name:
    :param port:
    :param namespace:
    :param app:
    :return:
    """
    log.info(f">>> Creating cluster service with name: {name}")
    srv_body = client.V1Service(metadata=client.V1ObjectMeta(name=name,
                                                             labels={"app": app} if app else None),
                                spec=client.V1ServiceSpec(type="ClusterIP",
                                                          selector=selector,
                                                          ports=[client.V1ServicePort(name=DEF_PORT_NAME,
                                                                                      protocol="TCP",
                                                                                      port=port)]))
    return client.CoreV1Api().create_namespaced_service(namespace=namespace, body=srv_body)


def _create_nodeport_endpointslice(service_name: str, address: str, target_port: int, namespace: str = None,
                                   app: str = None) -> client.V1EndpointSlice:
    """

    :param service_name:
    :param address:
    :param target_port:
    :param namespace:
    :param app:
    :return:
    """
    log.info(f">>> Creating endpointslice for service: {service_name}...")
    labels = {LABEL_K8S_ENDPOINTSLICE_SRV_NAME: service_name,
              LABEL_K8S_ENDPOINTSLICE_MGR: "controller.ptx-edge.org"}
    if app:
        labels["app"] = app
    eps_body = client.V1EndpointSlice(metadata=client.V1ObjectMeta(name=service_name,
                                                                   labels=labels),
                                      address_type="IPv4",
                                      ports=[client.V1ServicePort(name=DEF_PORT_NAME,
                                                                  app_protocol="http",
                                                                  protocol="TCP",
                                                                  port=target_port)],
                                      endpoints=[client.V1Endpoint(addresses=[address])])
    return client.DiscoveryV1Api().create_namespaced_endpoint_slice(namespace=namespace, body=eps_body)


def _patch_pod_labels(pod: str, namespace: str, zones: list[str]) -> client.V1Pod:
    log.info(f">>> Patching pod[{pod}]...")
    labels = dict.fromkeys(zones, "true")
    if len(zones) == 0:
        log.debug(f"No privacy zone label detected for pod[{pod}]! Using default zone ID: {CONFIG['def_zone']}")
        def_zone_id = CONFIG['def_zone']
    else:
        if len(zones) > 1:
            log.warning(f"Multiple privacy zone labels detected for pod[{pod}]! "
                        f"Selecting the first zone ID as default...")
        def_zone_id = sorted(map(lambda _l: _l.split('/')[-1].lower(), zones))[0]
    log.info(f"Selected default privacy zone: {def_zone_id}")
    labels[f"{LABEL_PTX_PRIVACY_ZONE}/default"] = def_zone_id
    labels[f"{LABEL_PTX_CONNECTOR}/id"] = f"pdc-{def_zone_id}"
    pod_patch = client.V1Pod(metadata=client.V1ObjectMeta(labels=labels))
    log.debug(f"Created pod patch:\n{dump_k8s_obj(pod_patch.to_dict())}")
    pod = client.CoreV1Api().patch_namespaced_pod(name=pod, namespace=namespace, body=pod_patch)
    log.debug(f"Patched pod:\n{dump_k8s_obj(pod.to_dict())}")
    return pod


########################################################################################################################

def create_headless_pdc_services(port: int, ip: str, namespace: str, app: str = None, force: bool = False, **kwargs):
    """

    :param port:
    :param ip:
    :param namespace:
    :param app:
    :param force:
    :param kwargs:
    :return:
    """
    try:
        zones = _collect_privacy_zone_labels(ip=ip)
        if len(zones) == 0:
            log.warning("No privacy zone label detected!")
            if force:
                log.info(f"Forcing to create PDC service with default name: {DEF_APP}")
                zones.append(None)
        elif len(zones) > 1:
            log.warning(f"Multiple privacy zone label detected for one node[{ip}]!")
            if force:
                log.info("Forcing to create PDC service for each privacy zone...")
            else:
                log.error("Skip creating PDC service...")
                zones.clear()
        for zone in zones:
            srv_name = f"{DEF_APP}-{zone.split('/')[-1]}".lower() if zone else DEF_APP
            try:
                srv = _create_headless_service(name=srv_name, port=port, namespace=namespace, app=app)
            except ApiException as e:
                if e.reason == 'Conflict' and force:
                    log.warning(f"Service[{srv_name}] already exists. Recreate resources...")
                    del_eps = _delete_endpointslice(name=srv_name, namespace=namespace)
                    log.info(f"Endpointslice[{srv_name}] deleted with status: {del_eps.status}")
                    del_srv = _delete_service(name=srv_name, namespace=namespace)
                    log.info(f"Service[{srv_name}] deleted with status: {del_srv.status}")
                    srv = _create_headless_service(name=srv_name, port=port, namespace=namespace, app=app)
                else:
                    raise
            log.debug(f"Created service:\n{dump_k8s_obj(srv.to_dict())}")
            eps = _create_nodeport_endpointslice(service_name=srv_name, address=ip, target_port=port,
                                                 namespace=namespace, app=app)
            log.debug(f"Created endpointslice:\n{dump_k8s_obj(eps.to_dict())}")
    except OpenApiException as e:
        log.error(f"Received error:\n{e}")
        sys.exit(os.EX_IOERR)


def create_clusterip_pdc_services(node: str, pod: str, namespace: str, port: int, app: str = None, force: bool = False,
                                  def_zone: str = None, **kwargs):
    try:
        zones = _collect_privacy_zone_labels(node=node)
        if len(zones) == 0 and not force:
            log.warning("No privacy zone label detected! Skip patching...")
        else:
            _patch_pod_labels(pod=pod, namespace=namespace, zones=zones)
        if not force:
            return
        elif len(zones) < 1:
            log.info(f"Forcing to create PDC service with default name: {DEF_APP}")
            zones.append(None)
        elif len(zones) > 1:
            log.warning(f"Multiple privacy zone label detected for one node[{node}]!")
            log.info("Forcing to create PDC service for each privacy zone...")
        for zone in zones:
            srv_name = f"{DEF_APP}-{zone.split('/')[-1]}".lower() if zone else DEF_APP
            selector = {'app': app, zone: "true"} if zone else {'app': app}
            try:
                srv = _create_cluster_service(name=srv_name, port=port, namespace=namespace, app=app,
                                              selector=selector)
            except ApiException as e:
                if e.reason == 'Conflict':
                    log.warning(f"Service[{srv_name}] already exists. Recreate resources...")
                    del_srv = _delete_service(name=srv_name, namespace=namespace)
                    log.info(f"Service[{srv_name}] deleted with status: {del_srv.status}")
                    srv = _create_cluster_service(name=srv_name, port=port, namespace=namespace, app=app,
                                                  selector=selector)
                else:
                    raise
            log.debug(f"Created service:\n{dump_k8s_obj(srv.to_dict())}")
    except OpenApiException as e:
        log.error(f"Received error:\n{e}")
        sys.exit(os.EX_IOERR)


########################################################################################################################


def main():
    parser = argparse.ArgumentParser(prog=pathlib.Path(__file__).name, description="PDC Service Creator")
    parser.add_argument("-t", "--type", type=str, required=True, help="Service type [headless,clusterip]")
    parser.add_argument("-p", "--port", type=int, help="Port bound on the node")
    parser.add_argument("-i", "--ip", type=str, help="Node IP address")
    parser.add_argument("--node", type=str, help="Assigned node name")
    parser.add_argument("--pod", type=str, help="Own pod name")
    parser.add_argument("-n", "--namespace", type=str, help="Namespace name")
    parser.add_argument("-a", "--app", type=str, help="Application name")
    parser.add_argument("-z", "--def_zone", type=str, help="Default privacy zone ID")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Force (re)creating services even if existed")
    parser.add_argument("-v", "--verbose", action="store_true", help="Make logging verbose")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.getLogger('kubernetes.client.rest').setLevel(logging.INFO)
    log.info(" PDC init START ".center(80, '#'))
    log.debug(f"Parsed CLI args: {args}")
    CONFIG.update(kv for kv in vars(args).items() if kv[1] is not None)
    if not all(map(lambda param: bool(CONFIG[param]), REQUIRED_FIELDS)):
        log.error(f"Missing one of the required parameters: {REQUIRED_FIELDS} from {CONFIG}")
        sys.exit(os.EX_CONFIG)
    log.debug(f"Configuration parameters: {CONFIG}")
    _load_config()
    log.info("Creating service(s) for PDC...")
    match args.type.upper():
        case "HEADLESS":
            create_headless_pdc_services(**CONFIG)
        case "CLUSTERIP":
            create_clusterip_pdc_services(**CONFIG)
        case _:
            log.error(f"Unrecognized type: {args.type}")
            sys.exit(os.EX_IOERR)
    log.info(" PDC init END ".center(80, '#'))


if __name__ == '__main__':
    main()
