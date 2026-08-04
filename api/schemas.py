"""HTTP request contracts for workflow operations."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CreateRunRequest(ApiModel):
    raw_requirement: str = Field(min_length=10, max_length=50_000)
    title: str = Field(default="New feature", min_length=1, max_length=200)
    simulate_test_failure: bool = False


class ResumeRunRequest(ApiModel):
    status: str
    actor: str = Field(min_length=1, max_length=200)
    comment: str | None = Field(default=None, max_length=2_000)
    artifact_id: str | None = Field(default=None, min_length=1, max_length=200)
    artifact_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_decision(self) -> "ResumeRunRequest":
        if self.status not in {"approved", "rejected"}:
            raise ValueError("status must be 'approved' or 'rejected'")
        if self.status == "rejected" and not self.comment:
            raise ValueError("a rejection must include a comment")
        if (self.artifact_id is None) != (self.artifact_version is None):
            raise ValueError("artifact_id and artifact_version must be provided together")
        return self
