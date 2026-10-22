"""Split each page by heading. Every chunk starts with 'Page title | Heading > Subheading' so it reads fine on its own."""
import re

from .config import settings

HEAD_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def _sections(text: str) -> list[dict]:
    secs, stack, buf = [], [], []

    def flush():
        body = "\n".join(buf).strip()
        if body:
            secs.append({"path": [h for _, h in stack if h], "body": body})
        buf.clear()

    for line in text.splitlines():
        m = HEAD_RE.match(line)
        if m:
            flush()
            level, title = len(m.group(1)), m.group(2).strip(" :")
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        else:
            buf.append(line)
    flush()
    return secs


def _explode(block: str, limit: int) -> list[str]:
    if len(block) <= limit:
        return [block]
    parts = block.split("\n") if "\n" in block else re.split(r"(?<=[.!?])\s+", block)
    out, cur = [], ""
    for p in parts:
        if cur and len(cur) + len(p) + 1 > limit:
            out.append(cur)
            cur = ""
        cur = f"{cur}\n{p}".strip() if "\n" in block else f"{cur} {p}".strip()
    if cur:
        out.append(cur)
    return out


def _pack(body: str, limit: int) -> list[str]:
    pieces = [x for b in re.split(r"\n\s*\n", body.strip()) for x in _explode(b.strip(), limit) if x.strip()]
    out, cur = [], ""
    for p in pieces:
        if cur and len(cur) + len(p) + 2 > limit:
            out.append(cur)
            cur = ""
        cur = f"{cur}\n\n{p}".strip()
    if cur:
        out.append(cur)
    return out


def chunk_page(page: dict, page_idx: int, limit: int | None = None) -> list[dict]:
    limit = limit or settings.chunk_chars
    chunks, carry = [], ""
    secs = _sections(page["text"])

    def emit(path, text):
        for part in _pack(text, limit):
            n = len(chunks)
            section = " > ".join(path[1:]) if len(path) > 1 else "Overview"
            chunks.append({
                "id": f"p{page_idx}-c{n}",
                "url": page["url"],
                "title": page["title"],
                "page_type": page["type"],
                "section": section,
                "text": part,
                "index_text": f"{page['title']} | {section}\n{part}",
            })

    for i, s in enumerate(secs):
        body = s["body"]
        if carry:                         # very short section, merge it into the next one
            body = carry + "\n\n" + body
            carry = ""
        if len(body) < 150 and i < len(secs) - 1:
            label = s["path"][-1] if s["path"] else ""
            carry = f"{label}: {body}" if label and not body.startswith(label) else body
            continue
        emit(s["path"], body)
    if carry:
        emit(secs[-1]["path"] if secs else [page["title"]], carry)
    return chunks


def chunk_pages(pages: list[dict]) -> list[dict]:
    return [c for i, p in enumerate(pages) for c in chunk_page(p, i)]
