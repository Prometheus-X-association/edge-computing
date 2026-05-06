#!/usr/bin/env python3
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
import argparse
import json
import pathlib

import yaml

OPENAPI_VERSION = "3.0.0"


def extract_openapi_scheme_from_crd(crd_file: pathlib.Path, scheme_dir: pathlib.Path, served: bool = False) -> None:
    """

    :param crd_file:
    :param scheme_dir:
    :param served:
    :return:
    """
    scheme_dir.mkdir(parents=True, exist_ok=True)
    crds = list(filter(bool, yaml.safe_load_all(crd_file.resolve(strict=True).read_text())))
    for crd in crds:
        for version in crd['spec']['versions']:
            if served and not version['served']:
                continue
            # Add CRD name and version info as extensions
            version['schema']['openAPIV3Schema'].update({
                "x-database-model": {
                    "group": crd['spec']['group'],
                    "version": version["name"],
                    "kind": crd['spec']['names']['kind'],
                    "singular": crd['spec']['names']['singular'],
                    "plural": crd['spec']['names']['plural'],
                }})
            data = {
                "openapi": OPENAPI_VERSION,
                "info": {
                    "title": crd['metadata']['name'],
                    "version": version["name"],
                },
                "paths": {},
                "components": {
                    "schemas": {
                        # crd['spec']['names']['kind']: ver['schema']['openAPIV3Schema']
                        crd['spec']['names']['shortNames'][0].upper(): version['schema']['openAPIV3Schema']
                    }
                }
            }
            with scheme_dir.joinpath(crd['spec']['names']['singular'] + ".json").open("w") as f:
                json.dump(data, f, indent=2, sort_keys=False)


def main():
    ################# Parse parameters
    parser = argparse.ArgumentParser(prog=pathlib.Path(__file__).name, description="K8s CRD-OpenAPI Schema Extractor")
    parser.add_argument('crd', type=pathlib.Path, help="Input k8s CRD file")
    parser.add_argument('schema_dir', type=pathlib.Path, default=argparse.SUPPRESS,
                        help="Extracted OpenAPI schema file")
    parser.add_argument("--served", action="store_true", required=False,
                        help="Extract only the served OpenAPI schema version")
    args = parser.parse_args()
    #################
    try:
        extract_openapi_scheme_from_crd(crd_file=args.crd, scheme_dir=args.schema_dir, served=args.served)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
