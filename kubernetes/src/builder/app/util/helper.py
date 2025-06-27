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
import configparser
import logging
import pprint
import time

log = logging.getLogger(__package__)

DEF_WAIT_SECONDS = 5


def print_config(cfg: configparser.ConfigParser):
    log.debug("Configuration:\n" + pprint.pformat([f"[{sec}] {k}: {v}" for sec in cfg for k, v in cfg.items(sec)],
                                                  indent=2, sort_dicts=False))


def wait_and_exit(_delay: int = DEF_WAIT_SECONDS):
    log.warning(f"Waiting for builder to finish[{_delay}s]...")
    time.sleep(_delay)
