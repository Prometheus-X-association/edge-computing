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
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class DataSourceAuth(object):
    scheme: str = None
    params: dict = None

    @classmethod
    def parse(cls, cfg: str | dict | None) -> Self:
        if isinstance(cfg, str):
            cfg = cfg.split(':')
            if len(cfg) == 3:
                return cls(scheme=cfg[0], params=dict(username=cfg[1], password=cfg[2]))
            elif len(cfg) == 2:
                return cls(scheme='basic', params=dict(username=cfg[0], password=cfg[1]))
            else:
                raise ValueError(f'Invalid datasource auth cfg: [scheme:]<username>:<passwd>! -- {cfg}')
        elif isinstance(cfg, dict):
            return cls(scheme=cfg['scheme'], params={k: v for k, v in cfg.items() if k != 'scheme'})
        elif cfg is None:
            return cls()
        else:
            raise ValueError(f'Invalid datasource auth scheme/params: {cfg}!')


@dataclass(frozen=True)
class DockerRegistryAuth(object):
    __DEF_DOCKER_REGISTRY: str = 'https://index.docker.io/v1/'

    on_behalf: str = None
    secret: str = None
    server: str = None

    @classmethod
    def parse(cls, cfg: str | dict) -> Self:
        if isinstance(cfg, str):
            cfg = cfg.rsplit('@', maxsplit=1)
            user_pass = cfg[0].split(':')
            if len(cfg) == 2 and len(user_pass) == 2:
                return cls(on_behalf=user_pass[0], secret=user_pass[1], server=cfg[1])
            elif len(user_pass) == 2:
                return cls(on_behalf=user_pass[0], secret=user_pass[1])
            else:
                raise ValueError(f'Invalid registry auth cfg: <on_behalf>:<secret>[@<server>]! -- {cfg}')
        elif isinstance(cfg, dict):
            return cls(on_behalf=cfg['on_behalf'], secret=cfg['secret'],
                       server=cfg.get('server', 'https://index.docker.io/v1/'))
        else:
            raise ValueError(f'Invalid registry auth username/password: {cfg}!')

    def to_str(self) -> str:
        return f"{self.on_behalf}:{self.secret}"

    def get_creds(self) -> tuple:
        return self.on_behalf, self.secret

    def get_registry(self) -> str:
        return self.server if self.server else self.__DEF_DOCKER_REGISTRY
