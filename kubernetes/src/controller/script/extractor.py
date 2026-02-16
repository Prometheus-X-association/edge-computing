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


def extract_openapi_scheme_from_crd(crd_file: pathlib.Path, scheme_file: pathlib.Path) -> None:
    """

    :param crd_file:
    :param scheme_file:
    :return:
    """
    crds = list(filter(bool, yaml.safe_load_all(crd_file.resolve(strict=True).read_text())))
    for crd in crds:
        name = crd['metadata']['name']
        kind = crd['spec']['names']['kind']
        for ver in crd['spec']['versions']:
            v3_scheme = ver['schema']['openAPIV3Schema']
            data = {
                "openapi": OPENAPI_VERSION,
                "info": {
                    "title": name,
                    "version": ver["name"],
                },
                "paths": {},
                "components": {
                    "schemas": {
                        kind: v3_scheme
                    }
                }
            }
            scheme_file.parent.mkdir(parents=True, exist_ok=True)
            with scheme_file.open("w") as f:
                json.dump(data, f, indent=2, sort_keys=False)


def main():
    ################# Parse parameters
    parser = argparse.ArgumentParser(prog=pathlib.Path(__file__).name, description="K8s CRD-OpenAPI Schema Extractor")
    parser.add_argument('crd', type=pathlib.Path, help="Input k8s CRD file")
    parser.add_argument('schema', type=pathlib.Path, help="Extracted OpenAPI schema file")
    args = parser.parse_args()
    #################
    try:
        extract_openapi_scheme_from_crd(crd_file=args.crd, scheme_file=args.schema)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
