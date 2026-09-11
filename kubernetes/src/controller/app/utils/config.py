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
import logging
import os
import pathlib

import jinja2.sandbox
import kopf
from benedict import benedict
from kubernetes.aio import config

from model.ptxedgeworker import PEW

### Controller version
__version__ = '1.0.0'

### Globally available objects
ENV_PREFIX = "CFG_"
# Required fields in the configuration
REQUIRED_FIELDS = ("builder.prefix", "builder.image")

### Default configuration
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


########################################################################################################################

async def load_k8s_config(logger: kopf.Logger,
                          **_) -> None:
    logger.info("Loading k8s in-cluster config...")
    config.load_incluster_config(try_refresh_token=True)


class ExcludeProbesFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return 'GET /healthz ' not in record.getMessage()


async def load_operator_config(settings: kopf.OperatorSettings,
                               memo: kopf.Memo,
                               logger: kopf.Logger,
                               **_) -> None:
    logger.info(f"Loading operator configuration...")
    # PTX-edge/controller related configurations
    # Read config items from envvars dynamically using global default values
    logger.debug(f"Loading configuration from envvars[{ENV_PREFIX}*]...")
    memo.CONFIG = load_config_from_env()
    logger.debug(f"Loaded configuration:\n" + str(memo.CONFIG.to_toml()))
    # Kopf-internal configurations
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(prefix=PEW.group)
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(prefix=PEW.group,
                                                                            key='last-handled-configuration')
    settings.persistence.finalizer = f"{PEW.group}/ewt-finalizer"  # Specify own finalizer
    settings.posting.loggers = False  # No auto-creating events from logs
    logging.getLogger('aiohttp.access').addFilter(ExcludeProbesFilter())  # Disable access logging
    logging.getLogger('kubernetes.aio.client.rest').setLevel(logging.WARNING)  # Disable k8s client dump logs


async def load_templates(memo: kopf.Memo,
                         logger: kopf.Logger,
                         **_) -> None:
    logger.info("Loading manifest templates...")
    memo.TEMPLATES = jinja2.sandbox.ImmutableSandboxedEnvironment(
        loader=jinja2.FileSystemLoader(pathlib.Path(__file__).parent.parent / "templates"),
        autoescape=False,
        auto_reload=False,
        optimized=True,
        trim_blocks=True,
        lstrip_blocks=True,
        enable_async=True,
        # extensions=['jinja2.ext.do']
    )
    logger.debug(f"Loaded templates: {memo.TEMPLATES.list_templates()}")
