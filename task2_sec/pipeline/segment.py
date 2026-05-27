"""Tier0 segmenter: TOC anchors + regex fallback on normalized body."""

from __future__ import annotations

import re
from enum import Enum

from bs4 import BeautifulSoup
from pydantic import BaseModel

from task2_sec.pipeline.normalize import normalize

# Line-start item headers only (avoids inline "see Item 1 above").
# Longer ids first so "Item 10" is not captured as Item "1".
_ITEM_ID = r"10|11|12|13|14|15|16|1[ABC]|7A|9A|9B|2|3|4|5|6|7|8|9|1"
HEADER_RE = re.compile(
    rf"(?m)^[ \t]*(?:ITEM|Item)\s+(?P<id>{_ITEM_ID})\s*[\.:\-]?\s*",
    re.IGNORECASE,
)


class SegmentMethod(str, Enum):
    TOC = "toc"
    REGEX = "regex"


class SegmentResult(BaseModel):
    item_id: str
    start: int
    end: int
    method: SegmentMethod


def assert_span_integrity(body: str, start: int, end: int, text: str) -> None:
    assert body[start:end] == text, f"span mismatch: {body[start:end]!r} != {text!r}"


def _normalize_item_id(raw: str) -> str:
    raw = raw.upper()
    if raw in {"1A", "1B", "1C", "7A", "9A", "9B"}:
        return raw
    return raw.lstrip("0") or raw


class Segmenter:
    def segment(self, html: str) -> tuple[str, list[SegmentResult]]:
        body = normalize(html)
        toc_hits = self._segment_from_toc(html, body)
        regex_hits = self._segment_from_regex(body)
        merged = self._merge_segments(toc_hits, regex_hits, len(body))
        return body, merged

    def _segment_from_toc(self, html: str, body: str) -> list[SegmentResult]:
        """Discover item ids from TOC anchors; positions resolved via regex on body."""
        soup = BeautifulSoup(html, "lxml")
        item_ids: set[str] = set()
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if not href.startswith("#"):
                continue
            anchor_id = href[1:]
            target = soup.find(id=anchor_id)
            if target is None:
                link_text = normalize(str(link))
                m = HEADER_RE.search(link_text.split("\n", 1)[0])
                if m:
                    item_ids.add(_normalize_item_id(m.group("id")))
                continue
            header_text = normalize(str(target)).split("\n", 1)[0].strip()
            m = HEADER_RE.search(header_text)
            if m:
                item_ids.add(_normalize_item_id(m.group("id")))

        results: list[SegmentResult] = []
        for item_id in sorted(item_ids, key=lambda x: self._find_content_header_start(body, x)):
            start = self._find_content_header_start(body, item_id)
            if start >= 0:
                results.append(
                    SegmentResult(
                        item_id=item_id,
                        start=start,
                        end=start,
                        method=SegmentMethod.TOC,
                    )
                )
        return results

    def _segment_from_regex(self, body: str) -> list[SegmentResult]:
        starts_by_id: dict[str, list[int]] = {}
        for m in HEADER_RE.finditer(body):
            item_id = _normalize_item_id(m.group("id"))
            starts_by_id.setdefault(item_id, []).append(m.start())

        hits: list[SegmentResult] = []
        for item_id, starts in starts_by_id.items():
            start = starts[-1] if len(starts) > 1 else starts[0]
            hits.append(
                SegmentResult(
                    item_id=item_id,
                    start=start,
                    end=start,
                    method=SegmentMethod.REGEX,
                )
            )
        return hits

    def _find_content_header_start(self, body: str, item_id: str) -> int:
        starts = [
            m.start()
            for m in HEADER_RE.finditer(body)
            if _normalize_item_id(m.group("id")) == item_id
        ]
        if not starts:
            return -1
        return starts[-1] if len(starts) > 1 else starts[0]

    def _merge_segments(
        self,
        toc: list[SegmentResult],
        regex: list[SegmentResult],
        body_len: int,
    ) -> list[SegmentResult]:
        by_id: dict[str, SegmentResult] = {}
        for seg in sorted(toc + regex, key=lambda s: (s.start, s.item_id)):
            existing = by_id.get(seg.item_id)
            if existing is None:
                by_id[seg.item_id] = seg
                continue
            # Prefer regex (content header position); TOC confirms id only.
            if seg.method == SegmentMethod.REGEX and existing.method != SegmentMethod.REGEX:
                by_id[seg.item_id] = seg
            elif seg.method == existing.method and seg.start > existing.start:
                by_id[seg.item_id] = seg

        ordered = sorted(by_id.values(), key=lambda s: s.start)
        for i, seg in enumerate(ordered):
            end = ordered[i + 1].start if i + 1 < len(ordered) else body_len
            seg.end = end
        return ordered
