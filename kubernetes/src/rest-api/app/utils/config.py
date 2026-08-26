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
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PTXEdgeApiConfig(BaseSettings):
    # Also auto-read from envvars
    ROOT_PATH: str = Field(default="/")
    WORKER_NS: str = Field(default="ptx-edge")
    #
    model_config = SettingsConfigDict(env_prefix='API_',
                                      case_sensitive=False)


CONFIG = PTXEdgeApiConfig()
