from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class MeetingFields(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=240)
    started_at: datetime | None = None

    @field_validator("started_at")
    @classmethod
    def aware_date(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Meeting time must include a timezone.")
        return value


class ParticipantFields(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid", str_strip_whitespace=True)
    display_name: str = Field(min_length=1, max_length=120)
    speaker_key: str = Field(min_length=1, max_length=160)
    user_id: UUID | None = None
