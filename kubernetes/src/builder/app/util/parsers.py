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
import enum
from dataclasses import dataclass, fields
from typing import Self

from app.util.helper import str2bool


class DataSourceAuthScheme(enum.StrEnum):
    BASIC = 'basic'
    DIGEST = 'digest'


@dataclass(frozen=True)
class DataSourceAuth(object):
    scheme: DataSourceAuthScheme = DataSourceAuthScheme.BASIC
    user: str = None
    secret: str = None
    insecure: bool = False

    @classmethod
    def parse(cls, cfg: str | dict | None) -> Self:
        if isinstance(cfg, str):
            if cfg.startswith('!'):
                insecure, cfg = True, cfg[1:]
            else:
                insecure = False
            cfg = cfg.split(':')
            if len(cfg) == 3:
                return cls(DataSourceAuthScheme(scheme=cfg[0]), user=cfg[1], secret=cfg[2], insecure=insecure)
            elif len(cfg) == 2:
                return cls(user=cfg[0], secret=cfg[1], insecure=insecure)
            else:
                raise ValueError(f'Invalid datasource auth cfg: [!][scheme:]<user>:<secret> -- {cfg}')
        elif isinstance(cfg, dict):
            return cls(**cfg)
        elif cfg is None:
            return cls()
        else:
            raise ValueError(f'Invalid datasource auth scheme/params: {cfg}!')

    def to_str(self) -> str:
        return f"{self.__class__.__name__}[scheme={self.scheme},user={self.user},secret=*****,insecure={self.insecure}]"

    def __str__(self):
        return self.to_str()


@dataclass(frozen=True)
class DockerRegistryAuth(object):
    server: str = 'https://index.docker.io/v1/'
    user: str = None
    secret: str = None
    insecure: bool = False
    ca_dir: str = None

    @classmethod
    def parse(cls, cfg: str | dict | None) -> Self:
        if isinstance(cfg, str):
            if cfg.endswith('!'):
                insecure, cfg = True, cfg[:-1]
            else:
                insecure = False
            cfg = cfg.rsplit('@', maxsplit=1)
            user_pass = cfg[0].split(':')
            if len(cfg) == 2 and len(user_pass) == 2:
                return cls(user=user_pass[0], secret=user_pass[1], server=cfg[1], insecure=insecure)
            elif len(user_pass) == 2:
                return cls(user=user_pass[0], secret=user_pass[1], insecure=insecure)
            else:
                raise ValueError(f'Invalid registry auth cfg: <user>:<secret>[@<server>][!] -- {cfg}')
        elif isinstance(cfg, dict):
            return cls(**{f.name: str2bool(cfg[f.name]) if f.type is bool else cfg[f.name]
                          for f in fields(cls) if f.name in cfg})
        elif cfg is None:
            return cls()
        else:
            raise ValueError(f'Invalid registry auth username/password: {cfg}!')

    def to_str(self) -> str:
        return (f"{self.__class__.__name__}[server={self.server},user={self.user},secret=*****,"
                f"insecure={self.insecure},ca_dir={self.ca_dir}]")

    def get_creds(self) -> tuple[str, str]:
        return self.user, self.secret
