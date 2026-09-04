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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expess or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

# Controller version
__version__ = '1.0.0'

import kopf
from benedict import benedict

### Globally available objects
ENV_PREFIX = "CFG_"
# Required fields in the configuration
REQUIRED_FIELDS = ("builder.prefix", "builder.image")

DEF_CONFIG = {
    "controller": {
        "manager": f"{os.getenv('NAMESPACE', "ptx-edge")}-{os.getenv('HOSTNAME', "controller")}"
    }
}


def load_config_from_env():
    cfg = benedict(DEF_CONFIG)
    envvars = [(k, int(v)) if v.isnumeric() else (k, v) for k, v in os.environ.items() if k.startswith(ENV_PREFIX)]
    env_cfg = benedict.from_toml("\n".join(f'{k.removeprefix(ENV_PREFIX).replace('_', '.').lower()}="{v}"'
                                           for k, v in envvars))
    cfg.merge(env_cfg)
    if not all(map(lambda _p: cfg.get(_p) is not None, REQUIRED_FIELDS)):
        raise kopf.PermanentError(f"Missing one of the required configurations: {REQUIRED_FIELDS} from {cfg}!")
    return cfg
