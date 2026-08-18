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
import pathlib
import pprint

import jinja2
import yaml

from model.ptxedgeworker import PEW

CONFIG = {
    'registry': {
        'path': 'registry.k3d.local:5000'
    },
    'scheduler': {
        'name': 'ptx-edge-scheduler'
    },
    'builder': {
        'name': 'builder',
        'image': 'ptx-edge/builder:1.0',
        'port': 9999
    },
    'pdc': {
        # 'host': 'pdc-zone-data-0.ptx-edge.svc.cluster.local',
        # 'port': 3000,
        'secret': 'pdc-secrets-env'
    }
}


def test_template(template: str, values: str | pathlib.Path):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(pathlib.Path(__file__).parent / '../app/templates'),
                             autoescape=False,
                             auto_reload=False,
                             optimized=True,
                             trim_blocks=True,
                             lstrip_blocks=True,
                             extensions=['jinja2.ext.do'])
    template = env.get_template(template)
    print(f"Loaded template: {template}")
    print('=' * 80)
    with open(values) as f:
        pew_example = yaml.safe_load(f)
    pew = PEW.model_validate(pew_example, strict=False)
    print(f"Loaded value model:\n{pew.model_dump_json(indent=2)}")
    print('=' * 80)
    print(f"Defined config:\n{pprint.pformat(CONFIG)}")
    print('=' * 80)
    manifest = template.render(spec=pew.spec, name='test123', namespace="ptx-edge", cfg=CONFIG)
    print(f"Generated raw manifest:\n---\n{manifest}\n---")
    print('=' * 80)
    manifest = yaml.safe_load(manifest)
    print(f"Generated manifest:\n---\n{yaml.safe_dump(manifest, indent=2)}---")


if __name__ == '__main__':
    test_template("worker_deployment.yaml.jinja2", pathlib.Path(__file__).parent / "pew_example.yaml")
    test_template("worker_service.yaml.jinja2", pathlib.Path(__file__).parent / "pew_example.yaml")
    test_template("builder_service.yaml.jinja2", pathlib.Path(__file__).parent / "pew_example.yaml")
    test_template("worker_middleware.yaml.jinja2", pathlib.Path(__file__).parent / "pew_example.yaml")
    test_template("worker_ingress.yaml.jinja2", pathlib.Path(__file__).parent / "pew_example.yaml")
