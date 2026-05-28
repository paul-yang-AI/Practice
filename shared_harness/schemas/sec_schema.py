from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ItemStatus(str, Enum):
    EXTRACTED = "extracted"
    LOW_CONFIDENCE = "low_confidence"
    MISSING = "missing"
    INCORPORATED_BY_REFERENCE = "incorporated_by_reference"
    NOT_APPLICABLE = "not_applicable"


STANDARD_ITEMS: tuple[str, ...] = (
    "1",
    "1A",
    "1B",
    "1C",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "7A",
    "8",
    "9",
    "9A",
    "9B",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
)


class ItemRecord(BaseModel):
    item_id: str
    part: str | None = None
    status: ItemStatus
    text: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    segment_method: str | None = None
    warnings: list[str] = Field(default_factory=list)
    start: int | None = None
    end: int | None = None


class FilingExtraction(BaseModel):
    accession: str
    cik: str | None = None
    ticker: str | None = None
    items: list[ItemRecord]
