# Copyright 2026 Janos Czentye
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

log = logging.getLogger(__name__)


def setup_logging(verbosity: int):
    logging.basicConfig(level=logging.DEBUG if verbosity > 0 else logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.getLogger('kubernetes.client.rest').setLevel(
        logging.DEBUG if verbosity > 1 else logging.INFO if verbosity == 1 else logging.WARNING)
    log.debug(f"Set log level: {logging.getLevelName(logging.getLogger().level)}")
