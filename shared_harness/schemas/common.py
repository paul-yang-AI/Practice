from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class BoundaryDecision(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    confidence: float = Field(ge=0.0, le=1.0)
    source_quote: str | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "BoundaryDecision":
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class CriticVerdict(BaseModel):
    passed: bool
