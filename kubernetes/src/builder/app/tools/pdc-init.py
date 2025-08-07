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
import argparse
import logging
import os
import pathlib
import pprint
import sys

import yaml
from kubernetes import client
from kubernetes.client import OpenApiException, ApiException
from kubernetes.config import ConfigException
from kubernetes.config.incluster_config import InClusterConfigLoader

from app.util.helper import deep_filter

log = logging.getLogger(__package__)

PROJECTED_TOKEN_FILE = "/var/run/secrets/projected/token"
PROJECTED_CERT_FILE = "/var/run/secrets/projected/ca.crt"
PROJECTED_NS_FILE = "/var/run/secrets/projected/namespace"

K8S_ENDPOINTSLICE_SRV_NAME = 'kubernetes.io/service-name'
K8S_ENDPOINTSLICE_MGR = 'endpointslice.kubernetes.io/managed-by'

PTX_CONNECTOR_ENABLED = 'connector.dataspace.ptx.org/enabled'
PTX_PRIVACY_ZONE = 'privacy-zone.dataspace.ptx.org'

DEF_PDC_PORT = 30003
DEF_NS = "ptx-edge"
DEF_APP = "pdc"
DEF_PORT_NAME = "pdc-port"

CONFIG = {"ip": os.getenv("NODE_IP"),
          "port": int(os.getenv("NODE_PORT", default=DEF_PDC_PORT)),
          "namespace": os.getenv("NAMESPACE", default=DEF_NS),
          "app": os.getenv("APP_NAME", default=DEF_APP)}

REQUIRED_FIELDS = ("ip", "port", "namespace")


########################################################################################################################

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


def _collect_privacy_zone_labels(node_ip: str) -> list:
    """
    
    :param node_ip: 
    :return: 
    """
    log.debug(f">>> Collect Privacy Zone labels...")
    v1_node_list = client.CoreV1Api().list_node(label_selector=f'{PTX_CONNECTOR_ENABLED}=true')
    log.debug(f"Received nodes:\n{yaml.dump(deep_filter(v1_node_list.to_dict()))}")
    labels = [node.metadata.labels for node in v1_node_list.items
              if len(node.status.addresses) > 0 and
              list(filter(lambda a: a.type == 'InternalIP' and a.address == node_ip, node.status.addresses))]
    log.debug(f"Extracted labels of node[{node_ip}]:\n{pprint.pformat(labels)}")
    if len(labels) > 0:
        labels = list(filter(lambda l: l.startswith(PTX_PRIVACY_ZONE), labels.pop()))
    log.debug(f"Extracted privacy zone labels: {labels}")
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
    log.debug(f">>> Creating headless service with name: {name}")
    srv_body = client.V1Service(metadata=client.V1ObjectMeta(name=name,
                                                             labels={"app": app} if app else None),
                                spec=client.V1ServiceSpec(type="ClusterIP",
                                                          cluster_ip="None",
                                                          ports=[client.V1ServicePort(name=DEF_PORT_NAME,
                                                                                      protocol="TCP",
                                                                                      port=port,
                                                                                      target_port=port)]))
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
    log.debug(f">>> Creating endpointslice for service: {service_name}...")
    labels = {K8S_ENDPOINTSLICE_SRV_NAME: service_name,
              K8S_ENDPOINTSLICE_MGR: "controller.ptx-edge.org"}
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


########################################################################################################################

def create_pdc_services(port: int, ip: str, namespace: str, app: str = None, force: bool = False, **kwargs):
    _load_config()
    log.info("Creating service(s) for PDC...")
    try:
        zones = _collect_privacy_zone_labels(node_ip=ip)
        if len(zones) == 0:
            log.warning("No privacy zone label detected!")
            if force:
                log.info(f"Forcing to create PDC service with default name: {DEF_APP}")
                zones.append(None)
        for zone in _collect_privacy_zone_labels(node_ip=ip):
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
            log.debug(f"Created service:\n{yaml.dump(deep_filter(srv.to_dict()))}")
            eps = _create_nodeport_endpointslice(service_name=srv_name, address=ip, target_port=port,
                                                 namespace=namespace, app=app)
            log.debug(f"Created endpointslice:\n{yaml.dump(deep_filter(eps.to_dict()))}")
    except OpenApiException as e:
        log.error(f"Received error:\n{e}")
        sys.exit(os.EX_IOERR)


def main():
    parser = argparse.ArgumentParser(prog=pathlib.Path(__file__).name, description="Service Creator")
    parser.add_argument("-p", "--port", metavar="", type=int, help="Port bound on the node")
    parser.add_argument("-i", "--ip", type=str, help="Node IP address")
    parser.add_argument("-n", "--namespace", type=str, help="Namespace name")
    parser.add_argument("-a", "--app", type=str, help="Application name")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Recreate resource even if it already exists")
    parser.add_argument("-v", "--verbose", action="store_true", help="Make logging verbose")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.getLogger('kubernetes.client.rest').setLevel(logging.INFO)
    log.info(" Service Creator START ".center(80, '#'))
    log.debug(f"Parsed CLI args: {args}")
    CONFIG.update(kv for kv in vars(args).items() if kv[1] is not None)
    if not all(map(lambda param: bool(CONFIG[param]), ('ip', 'port', 'namespace'))):
        log.error(f"Missing one of required parameters: {REQUIRED_FIELDS} from {CONFIG}")
        sys.exit(os.EX_CONFIG)
    log.debug(f"Configuration parameters: {CONFIG}")
    create_pdc_services(**CONFIG)
    log.info(" Service Creator END ".center(80, '#'))


if __name__ == '__main__':
    main()
