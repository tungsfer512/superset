# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from flask_appbuilder.security.sqla.apis.user.schema import User
from flask_appbuilder.security.sqla.apis.user.validator import (
    PasswordComplexityValidator,
)
from marshmallow import fields, Schema, ValidationError
from marshmallow.fields import Boolean, Integer, String
from marshmallow.validate import Length

from superset.utils.display_timezone import is_known_time_zone

first_name_description = "The current user's first name"
last_name_description = "The current user's last name"
password_description = "The current user's password for authentication"  # noqa: S105
display_time_zone_description = (
    "IANA time zone name temporal data is displayed and filtered in for this "
    "user, e.g. `Asia/Ho_Chi_Minh`. An empty string clears the preference, "
    "falling back to the instance default."
)


def validate_display_time_zone(value: str) -> None:
    """Accept a known IANA time zone name, or an empty string to clear it."""
    if value and not is_known_time_zone(value):
        raise ValidationError(f"Unknown time zone: {value}")


class UserResponseSchema(Schema):
    id = Integer()
    username = String()
    email = String()
    first_name = String()
    last_name = String()
    is_active = Boolean()
    is_anonymous = Boolean()
    login_count = Integer()
    display_time_zone = String(
        metadata={"description": display_time_zone_description},
        dump_only=True,
    )


class CurrentUserPutSchema(Schema):
    model_cls = User

    first_name = fields.String(
        required=False,
        metadata={"description": first_name_description},
        validate=[Length(1, 64)],
    )
    last_name = fields.String(
        required=False,
        metadata={"description": last_name_description},
        validate=[Length(1, 64)],
    )
    password = fields.String(
        required=False,
        validate=[PasswordComplexityValidator()],
        metadata={"description": password_description},
    )
    display_time_zone = fields.String(
        required=False,
        allow_none=True,
        validate=[validate_display_time_zone],
        metadata={"description": display_time_zone_description},
    )
