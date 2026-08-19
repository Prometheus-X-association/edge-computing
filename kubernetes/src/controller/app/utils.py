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
import json
import logging
import os
import pprint
import typing
from textwrap import indent

import benedict
from kubernetes import client


def load_config_from_env(prefix: str):
    envvars = [(k, int(v)) if v.isnumeric() else (k, v) for k, v in os.environ.items() if k.startswith(prefix)]
    return benedict.benedict.from_toml("\n".join(f'{k.removeprefix(prefix).replace('_', '.').lower()}="{v}"'
                                                 for k, v in envvars))


def deep_json_filter(data: object, keep: typing.Callable = bool) -> object:
    """

    :param data:
    :param keep:
    :return:
    """
    if isinstance(data, dict):
        return dict(filter(lambda kv: bool(kv[1]), ((k, deep_json_filter(v, keep)) for k, v in data.items())))
    elif isinstance(data, (list, tuple, set)):
        return type(data)(filter(bool, (deep_json_filter(v, keep) for v in data)))
    elif keep(data):
        return data
    else:
        return None


def deep_openapi_filter(data: object, keep: typing.Callable = bool) -> object:
    """

    :param data:
    :param keep:
    :return:
    """
    if hasattr(data, "openapi_types"):
        return dict(filter(lambda kv: bool(kv[1]),
                           ((att, deep_openapi_filter(getattr(data, att), keep)) for att in data.openapi_types)))
    if isinstance(data, dict):
        return dict(filter(lambda kv: bool(kv[1]), ((k, deep_json_filter(v, keep)) for k, v in data.items())))
    elif isinstance(data, (list, tuple, set)):
        return type(data)(filter(bool, (deep_openapi_filter(v, keep) for v in data)))
    elif keep(data):
        return data
    else:
        return None


def sanitize_model(data: object, indent: int = 2) -> str:
    return pprint.pformat(deep_openapi_filter(data), indent=indent)


class ExcludeProbesFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return 'GET /healthz ' not in record.getMessage()


def convert_k8s_api_error(e: client.ApiException) -> str:
    return '\n'.join((f"Error received with status: {e.status} and reason: {e.reason}",
                      "HTTP response body:",
                      json.dumps(json.loads(str(e.body)) if e.body else '{}', indent=2)))
