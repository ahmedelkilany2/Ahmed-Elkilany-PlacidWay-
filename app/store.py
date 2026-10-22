"""SQLite storage for leads and unanswered questions."""
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from .config import settings

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def _conn():
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(settings.db_file)
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY, ts TEXT, name TEXT, email TEXT, interest TEXT, note TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS gaps(id INTEGER PRIMARY KEY, ts TEXT, question TEXT, query TEXT, reason TEXT, top_source TEXT)")
    return c


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add_lead(name: str, email: str, interest: str = "", note: str = "") -> None:
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO leads(ts,name,email,interest,note) VALUES (?,?,?,?,?)",
                  (_now(), name[:120], email[:200], interest[:200], note[:1000]))


def add_gap(question: str, query: str, reason: str, top_source: str = "") -> None:
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO gaps(ts,question,query,reason,top_source) VALUES (?,?,?,?,?)",
                  (_now(), question[:1000], query[:500], reason, top_source))


def list_rows(table: str, limit: int = 200) -> list[dict]:
    assert table in ("leads", "gaps")
    with closing(_conn()) as c:
        return [dict(r) for r in c.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limit,))]


def gap_summary() -> list[dict]:
    with closing(_conn()) as c:
        return [dict(r) for r in c.execute(
            "SELECT query, reason, COUNT(*) AS times, MAX(ts) AS last_seen FROM gaps "
            "WHERE reason IN ('not_in_content','weak_retrieval') GROUP BY lower(query), reason ORDER BY times DESC LIMIT 50")]
