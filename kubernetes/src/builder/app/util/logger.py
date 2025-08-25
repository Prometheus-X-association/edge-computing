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
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

SUB_MODULES = ('kubernetes.client.rest',)


def set_logging_level(verbosity: int = 0):
    if verbosity < 1:
        logging.getLogger().setLevel(logging.INFO)
        for submodule in SUB_MODULES:
            logging.getLogger(submodule).setLevel(logging.WARNING)
    elif verbosity == 1:
        logging.getLogger().setLevel(logging.DEBUG)
        for submodule in SUB_MODULES:
            logging.getLogger(submodule).setLevel(logging.INFO)
    elif verbosity > 1:
        for submodule in SUB_MODULES:
            logging.getLogger(submodule).setLevel(logging.DEBUG)
