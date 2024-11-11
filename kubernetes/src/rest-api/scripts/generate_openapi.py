#!/usr/bin/env python3.12
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
import enum
import pathlib
import sys

import click

PROJECT_DIR: pathlib.Path = pathlib.Path(__file__).parent.parent.resolve()


class EXTFORMAT(enum.StrEnum):
    """Options for openapi specification format"""
    yaml: str = "yaml"
    json: str = "json"


@click.command(help="Generate OpenAPI specification")
@click.option("-t", "--type", "_type", type=click.Choice(tuple(EXTFORMAT.__annotations__),
                                                         case_sensitive=False),
              required=False, default="yaml", help="Specification format")
@click.option("-d", "--dir", "_dir", type=click.Path(path_type=pathlib.Path, dir_okay=True,
                                                     file_okay=False, writable=True, exists=True),
              required=False, default=PROJECT_DIR / "spec", help="Folder to save")
def generate_openapi(_type: str, _dir: str | pathlib.Path) -> None:
    """Generate OpenAPI specification"""
    sys.path.insert(0, str(PROJECT_DIR))
    from app.main import app
    with open(_dir / f"openapi.{_type}", "w") as f:
        api_spec = app.openapi()
        if _type == EXTFORMAT.yaml:
            import yaml
            yaml.dump(api_spec, f, indent=2, sort_keys=False)
        elif _type == EXTFORMAT.json:
            import json
            json.dump(api_spec, f, indent=2, sort_keys=False)
        else:
            raise ValueError(f"Unsupported type {_type}")


if __name__ == '__main__':
    generate_openapi()
