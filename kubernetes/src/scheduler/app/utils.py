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
import typing

import networkx as nx

log = logging.getLogger(__name__)


def setup_logging(verbosity: int):
    logging.basicConfig(level=logging.DEBUG if verbosity > 0 else logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.getLogger('kubernetes.client.rest').setLevel(
        logging.DEBUG if verbosity > 1 else logging.INFO if verbosity == 1 else logging.WARNING)
    log.debug(f"Set log level: {logging.getLevelName(logging.getLogger().level)}")


def deep_filter(data: object, keep: typing.Callable = bool) -> object:
    """

    :param data:
    :param keep:
    :return:
    """
    if isinstance(data, dict):
        return dict(filter(lambda kv: bool(kv[1]), ((k, deep_filter(v, keep)) for k, v in data.items())))
    elif isinstance(data, (list, tuple, set)):
        return type(data)(filter(bool, (deep_filter(v, keep) for v in data)))
    elif keep(data):
        return data
    else:
        return None


def nx_graph_to_str(obj: nx.Graph) -> str:
    return (f"\n{json.dumps(dict(obj.nodes()), indent=4, sort_keys=False)}"
            f"{json.dumps(dict(obj.adjacency()), indent=4, sort_keys=False) if obj.edges() else ''}")


def to_bool(s: str | bool) -> bool:
    return str(s).lower() in ('true', 'yes', 'on', '1')
