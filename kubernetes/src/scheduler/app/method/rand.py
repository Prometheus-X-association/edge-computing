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
import random

from app.k8s import get_available_nodes

log = logging.getLogger(__name__)


def do_random_pod_assignment() -> str:
    log.info("Initiate RANDOM node selection")
    node_list = [n.metadata.name for n in get_available_nodes()]
    log.debug(f"Available nodes: {node_list}")
    log.info("Apply random node selection...")
    selected_node = random.choice(node_list)
    log.info(f"Selected node: {selected_node}")
    return selected_node
