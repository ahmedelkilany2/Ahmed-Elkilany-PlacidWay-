import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")   # read settings from the .env file if it exists


def _f(name, default):
    return float(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("DATA_DIR", ROOT / "data"))
    llm_api_key: str = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    llm_model: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    crawler_contact: str = os.getenv("CRAWLER_CONTACT", "contact-not-set")
    crawl_delay: float = _f("CRAWL_DELAY_SECONDS", 1.0)
    embeddings: bool = os.getenv("EMBEDDINGS", "on").lower() != "off"
    embed_model: str = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    admin_token: str = os.getenv("ADMIN_TOKEN", "")
    refresh_hours: float = _f("REFRESH_INTERVAL_HOURS", 24)
    lead_webhook: str = os.getenv("LEAD_WEBHOOK_URL", "")
    # retrieval gate: refuse to answer when BOTH signals are weak (tunable, see README)
    min_dense: float = _f("MIN_DENSE_SIM", 0.35)
    min_coverage: float = _f("MIN_COVERAGE", 0.3)   # share of query words found in the best chunk
    top_k: int = int(os.getenv("TOP_K", 6))
    chunk_chars: int = int(os.getenv("CHUNK_CHARS", 1100))

    @property
    def user_agent(self) -> str:
        return f"PlacidWayKnowledgeBot/1.0 (assessment project; contact: {self.crawler_contact})"

    @property
    def pages_file(self) -> Path:
        return self.data_dir / "pages.json"

    @property
    def db_file(self) -> Path:
        return self.data_dir / "app.db"


settings = Settings()
