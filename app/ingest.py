"""Crawler and page cleaner.

Most of each PlacidWay page is navigation and footer. Package pages also end with price cards
for other clinics (e.g. "Price starting from $33,400"), which must not end up in the index.
So we keep only the main article (from the H1 to "Request your Free Quote"), turn tables into
one line per row, and add a short facts block built from the page metadata.
"""
import hashlib
import json
import logging
import re
import time
import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as to_md

from .config import settings
from .sources import SOURCES

log = logging.getLogger("ingest")

# Sections that are site furniture or cross-promotion -> dropped (level-aware).
DROP_HEADINGS = re.compile(
    r"^(medical center reviews|package price|share this listing|related experiences|accreditations)", re.I)
# Everything from here down is footer / recommendations for other clinics -> dropped.
STOP_HEADINGS = re.compile(r"^(request your free quote|trusted medical tourism platform)", re.I)
NOISE_LINE = re.compile(
    r"^(copy link|chat with center|load more|get your quote now!?|send|×|"
    r"please validate your recaptcha.*|i agree to the.*|select a (specific )?treatment.*|"
    r"\d[\d.,]*[kKmM]?(\s+\d+)*)$", re.I)
ACTION_COLUMN = re.compile(r"^(actions?|rating / reviews)$", re.I)
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


# --------------------------------------------------------------------------- fetching
class Fetcher:
    """Checks robots.txt, sends a clear User-Agent, about 1 request per second, retries on errors."""

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": settings.user_agent, "Accept-Language": "en"})
        self._robots = {}
        self._last = 0.0

    def _throttle(self):
        wait = settings.crawl_delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def allowed(self, url: str) -> bool:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        rp = self._robots.get(base)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            self._throttle()
            try:
                r = self.s.get(base + "/robots.txt", timeout=15)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except requests.RequestException:
                rp.parse(["User-agent: *", "Disallow: /"])  # if robots.txt can't be read, don't crawl
            self._robots[base] = rp
        return rp.can_fetch(settings.user_agent, url)

    def get(self, url: str) -> str:
        if not self.allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        for attempt in range(3):
            self._throttle()
            try:
                r = self.s.get(url, timeout=25)
                if r.status_code == 429 or r.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {r.status_code}")
                r.raise_for_status()
                return r.text
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 ** (attempt + 1))
        raise RuntimeError("unreachable")


# --------------------------------------------------------------------------- cleaning
def _txt(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def _flatten_tables(soup: BeautifulSoup) -> None:
    """Turn each table row into a line like 'Procedure: Breast Cancer; Price in USD: $18995' so the column names travel with the value."""
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            table.decompose()
            continue
        headers = [_txt(c) for c in rows[0].find_all(["th", "td"])]
        ul = soup.new_tag("ul")
        for r in rows[1:]:
            cells = [_txt(c) for c in r.find_all(["td", "th"])]
            if not cells or not cells[0]:      # price-only row with no procedure name, skip it
                continue
            pairs, prev = [], None
            for h, c in zip(headers, cells):
                if not c or c == prev or ACTION_COLUMN.match(h):
                    prev = c
                    continue
                pairs.append(f"{h}: {c}")
                prev = c
            if pairs:
                li = soup.new_tag("li")
                li.string = "; ".join(pairs)
                ul.append(li)
        table.replace_with(ul)


def _filter_sections(md: str) -> str:
    lines = md.splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(r"^#\s+\S", l)), 0)
    out, skip_level = [], None
    for l in lines[start:]:
        m = HEAD_RE.match(l)
        if m:
            level, title = len(m.group(1)), m.group(2).strip(" :")
            if STOP_HEADINGS.search(title):
                break
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if skip_level is None and DROP_HEADINGS.search(title):
                skip_level = level
        if skip_level is None and not NOISE_LINE.match(l.strip()):
            out.append(l.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def extract(html: str, url: str, page_type: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    meta = {}
    for m in soup.find_all("meta"):
        key = m.get("property") or m.get("name")
        if key and m.get("content"):
            meta[key] = m["content"].strip()
    for t in soup(["script", "style", "noscript", "svg", "iframe", "form", "img", "picture", "video"]):
        t.decompose()
    _flatten_tables(soup)

    md = to_md(str(soup.body or soup), heading_style="ATX", bullets="-")
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)                      # images
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)                  # links -> text
    md = re.sub(r"[ \t]+\n", "\n", md)
    price_line = re.search(r"\$\s?([\d,]+(?:\.\d+)?)\s+Price starting from", md)   # grab before the reviews block is dropped
    body = _filter_sections(md)

    h1 = re.search(r"^#\s+(.+)$", body, re.M)
    title = h1.group(1).strip() if h1 else (soup.title.string.strip() if soup.title else url)

    facts = [f"Page type: {page_type}", f"Source URL: {url}"]
    if meta.get("description"):
        facts.append(f"Page summary: {meta['description']}")
    if meta.get("product:price.amount"):
        facts.append(f"Listed price (page metadata): {meta['product:price.amount']} {meta.get('product:price.currency', 'USD')}")
    elif price_line:
        facts.append(f"Price starting from (as shown on page): ${price_line.group(1)} USD")
    if h1:
        body = body.replace(h1.group(0), h1.group(0) + "\n\n" + "\n".join(f"- {f}" for f in facts), 1)
    else:
        body = f"# {title}\n\n" + "\n".join(f"- {f}" for f in facts) + "\n\n" + body

    return {
        "url": url,
        "type": page_type,
        "title": title,
        "text": body,
        "hash": hashlib.sha256(body.encode()).hexdigest()[:16],
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stale": False,
    }


# --------------------------------------------------------------------------- crawl + persist
def load_pages() -> list[dict]:
    if settings.pages_file.exists():
        return json.loads(settings.pages_file.read_text())["pages"]
    return []


def crawl() -> tuple[list[dict], dict]:
    """Fetch all source pages. If one fails, keep its previous copy (marked stale)."""
    previous = {p["url"]: p for p in load_pages()}
    fetcher, pages = Fetcher(), []
    report = {"changed": [], "unchanged": [], "failed": [], "new": []}
    for src in SOURCES:
        url = src["url"]
        try:
            page = extract(fetcher.get(url), url, src["type"])
            old = previous.get(url)
            bucket = "new" if not old else ("unchanged" if old["hash"] == page["hash"] else "changed")
            report[bucket].append(url)
            pages.append(page)
            log.info("%s %s (%d chars)", bucket, url, len(page["text"]))
        except Exception as e:  # noqa: BLE001
            log.error("failed %s: %s", url, e)
            report["failed"].append({"url": url, "error": str(e)})
            if url in previous:
                pages.append({**previous[url], "stale": True})
    return pages, report


def save_pages(pages: list[dict]) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    tmp = settings.pages_file.with_suffix(".tmp")
    tmp.write_text(json.dumps({"saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "pages": pages}, ensure_ascii=False, indent=1))
    tmp.replace(settings.pages_file)  # replace the file in one step


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    pages, rep = crawl()
    if pages:
        save_pages(pages)
    print(json.dumps(rep, indent=2))
