"""Extract per-item HTML snippets from original filing markup for faithful display."""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag

warnings.filterwarnings("ignore", category=UserWarning, message=".*XML.*")

from task2_sec.pipeline.normalize import normalize
from task2_sec.pipeline.segment import HEADER_RE, SegmentResult, _normalize_item_id

_MAX_SNIPPET_CHARS = 400_000
_HEADER_TAGS = frozenset(
    {"p", "div", "td", "th", "span", "b", "strong", "font", "a", "h1", "h2", "h3", "h4", "h5", "h6"}
)
_ITEM_HEADER_LINE = re.compile(
    r"^\s*(?:ITEM|Item)\s+(10|11|12|13|14|15|16|1[ABC]|7A|9A|9B|2|3|4|5|6|7|8|9|1)\s*[\.:\-\u2014]?\s*",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _HeaderMarker:
    item_id: str
    anchor_id: str | None
    body_offset: int
    header_text: str


def attach_html_snippets(
    html: str,
    body: str,
    segments: list[SegmentResult],
    items: list,
) -> None:
    """Populate ``html_snippet`` and ``source_anchor`` on extracted items in-place."""
    if not html.strip() or not segments:
        return

    markers = _collect_header_markers(html, body)
    if not markers:
        return

    ordered = sorted(segments, key=lambda s: s.start)
    by_id = {item.item_id: item for item in items}

    for idx, seg in enumerate(ordered):
        start = _best_marker(markers, seg)
        if start is None:
            continue
        next_seg = ordered[idx + 1] if idx + 1 < len(ordered) else None
        end = _best_marker(markers, next_seg) if next_seg else None
        snippet = _extract_between(html, body, start, end)
        if not snippet:
            continue
        item = by_id.get(seg.item_id)
        if item is None or item.text is None:
            continue
        item.html_snippet = snippet
        item.source_anchor = start.anchor_id


def _collect_header_markers(html: str, body: str) -> list[_HeaderMarker]:
    soup = BeautifulSoup(html, "lxml")
    root = soup.body or soup
    markers: list[_HeaderMarker] = []
    seen: set[tuple[str, str]] = set()

    for link in root.find_all("a", href=True):
        href = link.get("href", "")
        if not isinstance(href, str) or not href.startswith("#"):
            continue
        anchor_id = href[1:]
        target = root.find(id=anchor_id)
        if target is None:
            continue
        header_text = normalize(str(target)).split("\n", 1)[0].strip()
        item_id = _item_id_from_text(header_text)
        if not item_id:
            continue
        key = (item_id, anchor_id)
        if key in seen:
            continue
        seen.add(key)
        markers.append(
            _HeaderMarker(
                item_id=item_id,
                anchor_id=anchor_id,
                body_offset=_body_offset_for_item(body, item_id),
                header_text=header_text[:120],
            )
        )

    for tag in root.find_all(_HEADER_TAGS):
        if not isinstance(tag, Tag):
            continue
        if tag.find(_HEADER_TAGS):
            continue
        first_line = tag.get_text("\n", strip=True).split("\n", 1)[0].strip()
        if not first_line or len(first_line) > 240:
            continue
        item_id = _item_id_from_text(first_line)
        if not item_id:
            continue
        anchor_id = tag.get("id") or tag.get("name")
        if isinstance(anchor_id, list):
            anchor_id = anchor_id[0] if anchor_id else None
        anchor_key = str(anchor_id) if anchor_id else first_line[:40]
        key = (item_id, anchor_key)
        if key in seen:
            continue
        seen.add(key)
        markers.append(
            _HeaderMarker(
                item_id=item_id,
                anchor_id=str(anchor_id) if anchor_id else None,
                body_offset=_body_offset_for_header(body, first_line, item_id),
                header_text=first_line[:120],
            )
        )

    return sorted(markers, key=lambda m: m.body_offset)


def _item_id_from_text(text: str) -> str | None:
    m = HEADER_RE.search(text)
    if m:
        return _normalize_item_id(m.group("id"))
    m = _ITEM_HEADER_LINE.match(text.strip())
    if m:
        return _normalize_item_id(m.group(1))
    return None


def _body_offset_for_item(body: str, item_id: str) -> int:
    offsets = [m.start() for m in HEADER_RE.finditer(body) if _normalize_item_id(m.group("id")) == item_id]
    if not offsets:
        return len(body)
    return _pick_best_offset(offsets, len(body))


def _body_offset_for_header(body: str, header_line: str, item_id: str) -> int:
    needle = header_line[: min(60, len(header_line))]
    pos = body.find(needle)
    if pos >= 0:
        return pos
    return _body_offset_for_item(body, item_id)


def _pick_best_offset(offsets: list[int], body_len: int) -> int:
    if len(offsets) == 1:
        return offsets[0]
    if body_len > 20000:
        lo = body_len * 5 // 100
        hi = body_len - lo
        content = [o for o in offsets if lo < o < hi]
        if content:
            return content[0]
    return offsets[-1]


def _best_marker(markers: list[_HeaderMarker], seg: SegmentResult | None) -> _HeaderMarker | None:
    if seg is None:
        return None
    candidates = [m for m in markers if m.item_id == seg.item_id]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    return min(candidates, key=lambda m: abs(m.body_offset - seg.start))


def _find_marker_element(root: Tag, marker: _HeaderMarker) -> Tag | None:
    if marker.anchor_id:
        found = root.find(id=marker.anchor_id)
        if isinstance(found, Tag):
            return found
    needle = marker.header_text[: min(48, len(marker.header_text))]
    for tag in root.find_all(_HEADER_TAGS):
        first = tag.get_text("\n", strip=True).split("\n", 1)[0].strip()
        if first.startswith(needle[: min(32, len(needle))]) or needle.startswith(first[:32]):
            return tag
    return None


def _extract_between(
    html: str,
    body: str,
    start: _HeaderMarker,
    end: _HeaderMarker | None,
) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    root = soup.body or soup
    start_el = _find_marker_element(root, start)
    if start_el is None:
        return _extract_by_raw_html(html, body, start, end)
    end_el = _find_marker_element(root, end) if end else None

    parts: list[str] = []
    if start.anchor_id:
        parts.append(f'<a id="{start.anchor_id}"></a>')
    elif start_el.get("id"):
        parts.append(f'<a id="{start_el.get("id")}"></a>')

    for node in _iter_range(start_el, end_el):
        if isinstance(node, Tag):
            parts.append(str(node))
        elif isinstance(node, NavigableString):
            text = str(node)
            if text.strip():
                parts.append(text)

    snippet = _sanitize_html_snippet("".join(parts))
    if len(snippet) < 40:
        snippet = _extract_by_raw_html(html, body, start, end)
    if snippet and len(snippet) > _MAX_SNIPPET_CHARS:
        snippet = snippet[:_MAX_SNIPPET_CHARS] + "\n<!-- truncated -->"
    return snippet or None


def _iter_range(start_el: Tag, end_el: Tag | None):
    yield start_el
    for sibling in start_el.next_siblings:
        if end_el is not None and sibling is end_el:
            break
        if isinstance(sibling, Tag) and end_el is not None:
            if sibling is end_el or end_el in sibling.descendants:
                break
        yield sibling


def _extract_by_raw_html(
    html: str,
    body: str,
    start: _HeaderMarker,
    end: _HeaderMarker | None,
) -> str | None:
    start_line = start.header_text or f"Item {start.item_id}"
    start_pos = _find_in_html(html, start_line)
    if start_pos < 0:
        start_pos = _find_in_html(html, f"Item {start.item_id}")
    if start_pos < 0:
        return None

    end_pos = len(html)
    if end is not None:
        end_line = end.header_text or f"Item {end.item_id}"
        next_pos = _find_in_html(html, end_line, start_pos + 100)
        if next_pos < 0:
            next_pos = _find_in_html(html, f"Item {end.item_id}", start_pos + 100)
        if next_pos > start_pos:
            end_pos = next_pos

    return _sanitize_html_snippet(html[start_pos:end_pos])


def _find_in_html(html: str, needle: str, start: int = 0) -> int:
    if not needle:
        return -1
    chunk = needle[: min(48, len(needle))]
    return html.lower().find(chunk.lower(), start)


def _sanitize_html_snippet(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style", "noscript", "iframe", "object", "embed"]):
        tag.decompose()
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag) or tag.attrs is None:
            continue
        for attr in list(tag.attrs):
            lower = attr.lower()
            if lower.startswith("on") or lower == "srcdoc":
                del tag.attrs[attr]
            if lower == "href":
                href = tag.get("href", "")
                if isinstance(href, str) and href.lower().startswith("javascript:"):
                    del tag.attrs["href"]
    rendered = str(soup.body.decode_contents()) if soup.body else str(soup)
    return rendered.strip()
