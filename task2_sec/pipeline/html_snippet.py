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

    # Parse the (potentially multi-MB) filing once and reuse the tree for both
    # marker collection and per-item extraction. Re-parsing per item was the
    # dominant local cost, especially for large iXBRL filings (e.g. INTC).
    soup = BeautifulSoup(html, "lxml")
    root = soup.body or soup

    markers = _collect_header_markers(root, body)

    ordered = sorted(segments, key=lambda s: s.start)
    by_id = {item.item_id: item for item in items}

    for idx, seg in enumerate(ordered):
        next_seg = ordered[idx + 1] if idx + 1 < len(ordered) else None
        start = _best_marker(markers, seg) or _marker_from_body(body, seg)
        end = None
        if next_seg is not None:
            end = _best_marker(markers, next_seg) or _marker_from_body(body, next_seg)
        snippet = _extract_between(root, html, body, start, end)
        if not snippet:
            continue
        item = by_id.get(seg.item_id)
        if item is None or item.text is None:
            continue
        item.html_snippet = snippet
        item.source_anchor = start.anchor_id


def _marker_from_body(body: str, seg: SegmentResult) -> _HeaderMarker:
    """Synthesize a header marker from the segment's body text.

    Used when DOM/TOC marker discovery fails (e.g. Citi's incorporation-by-
    reference filing) so extraction is still attempted instead of bailing.
    """
    segment_text = body[seg.start : seg.end]
    first_line = segment_text.lstrip().split("\n", 1)[0].strip()
    header_text = first_line[:120] if first_line else f"Item {seg.item_id}"
    return _HeaderMarker(
        item_id=seg.item_id,
        anchor_id=None,
        body_offset=seg.start,
        header_text=header_text,
    )


def _collect_header_markers(root: Tag, body: str) -> list[_HeaderMarker]:
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
    root: Tag,
    html: str,
    body: str,
    start: _HeaderMarker,
    end: _HeaderMarker | None,
) -> str | None:
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
    # Pick the content occurrence, not the first hit. In a 10-K the first
    # textual match of an item header is the Table of Contents at the very top
    # of the document; slicing from there yields front-matter instead of the
    # actual section (the INTC iXBRL "stuck at the beginning" bug).
    start_pos = _find_best_in_html(html, start_line, fallback=f"Item {start.item_id}")
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


def _find_all_in_html(html: str, needle: str) -> list[int]:
    if not needle:
        return []
    chunk = needle[: min(48, len(needle))].lower()
    if not chunk:
        return []
    hay = html.lower()
    positions: list[int] = []
    pos = 0
    while True:
        idx = hay.find(chunk, pos)
        if idx < 0:
            break
        positions.append(idx)
        pos = idx + 1
    return positions


def _find_best_in_html(html: str, needle: str, *, fallback: str | None = None) -> int:
    positions = _find_all_in_html(html, needle)
    if not positions and fallback:
        positions = _find_all_in_html(html, fallback)
    if not positions:
        return -1
    return _pick_best_html_pos(positions, len(html))


def _pick_best_html_pos(positions: list[int], html_len: int) -> int:
    """Prefer the first occurrence inside the content body, skipping the TOC.

    Mirrors ``segment._pick_best_start``: the TOC sits in the first few percent
    (and any back-matter index in the last few percent) of large documents.
    """
    if len(positions) == 1:
        return positions[0]
    if html_len > 20000:
        lo = html_len * 8 // 100
        hi = html_len - html_len * 5 // 100
        content = [p for p in positions if lo < p < hi]
        if content:
            return content[0]
    return positions[-1]


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
