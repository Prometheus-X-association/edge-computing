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
import typing
from datetime import datetime, timezone

import kopf

from model.ptxedgeworker import PEWStatusCondition, PEWStatusConditionType, PEWStatusConditionStatus


def patch_condition(body: kopf.RawBody, condition: PEWStatusCondition) -> None:
    conditions = body.setdefault("status", {}).setdefault("conditions", [])
    if (existing_idx := next((i for i, c in enumerate(conditions)
                              if c['type'] == condition.type.value), None)) is not None:
        conditions.pop(existing_idx)
        conditions.insert(existing_idx, condition.model_dump(mode="json"))
    else:
        conditions.append(condition.model_dump(mode="json"))


########################################################################################################################

def patch_processed(body: kopf.RawBody, /, *, value: bool = True) -> None:
    patch_condition(body,
                    PEWStatusCondition(
                        type=PEWStatusConditionType.PROCESSED,
                        status=PEWStatusConditionStatus.TRUE if value else PEWStatusConditionStatus.FALSE,
                        lastTransitionTime=datetime.now(timezone.utc).replace(microsecond=0),
                        reason=f"Resources{'' if value else 'Not'}Processed",
                        message="Subresource states are changed."
                    ))


def patch_ready(body: kopf.RawBody, /, *, value: bool = True) -> None:
    body.setdefault("status", {})["ready"] = value
    patch_condition(body,
                    PEWStatusCondition(
                        type=PEWStatusConditionType.READY,
                        status=PEWStatusConditionStatus.TRUE if value else PEWStatusConditionStatus.FALSE,
                        lastTransitionTime=datetime.now(timezone.utc).replace(microsecond=0),
                        reason=f"Workers{'' if value else 'Not'}Available",
                        message="Worker is started running."
                    ))


def patch_exposed(body: kopf.RawBody, /, *, value: bool = True) -> None:
    body.setdefault("status", {})["exposed"] = value
    patch_condition(body,
                    PEWStatusCondition(
                        type=PEWStatusConditionType.EXPOSED,
                        status=PEWStatusConditionStatus.TRUE if value else PEWStatusConditionStatus.FALSE,
                        lastTransitionTime=datetime.now(timezone.utc).replace(microsecond=0),
                        reason=f"PublicInterfaces{'' if value else 'Not'}Exposed",
                        message="Interface availability is changed."
                    ))


def patch_succeeded(body: kopf.RawBody, /, *, value: bool = True) -> None:
    body.setdefault("status", {})["succeeded"] = value
    patch_condition(body,
                    PEWStatusCondition(
                        type=PEWStatusConditionType.SUCCEEDED,
                        status=PEWStatusConditionStatus.TRUE,
                        lastTransitionTime=datetime.now(timezone.utc).replace(microsecond=0),
                        reason=f"WorkersCompletedWithSuccess",
                        message="Worker is stopped running."
                    ))


def patch_failed(body: kopf.RawBody, /, *, value: bool = True) -> None:
    body.setdefault("status", {})["failed"] = value
    patch_condition(body,
                    PEWStatusCondition(
                        type=PEWStatusConditionType.FAILED,
                        status=PEWStatusConditionStatus.TRUE,
                        lastTransitionTime=datetime.now(timezone.utc).replace(microsecond=0),
                        reason=f"WorkersCompletedWithFailure",
                        message="Worker is stopped running."
                    ))


def patch_resulted(body: kopf.RawBody, /, *, result: typing.Any) -> None:
    ...
    # TODO
