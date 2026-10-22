import json
import logging
import re
import time

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError

from .config import settings

log = logging.getLogger("llm")


class LLMError(RuntimeError):
    pass


class LLM:
    def __init__(self):
        if not settings.llm_api_key:
            log.warning("LLM_API_KEY is not set - chat will return an error until it is.")
        self.client = OpenAI(api_key=settings.llm_api_key or "missing", base_url=settings.llm_base_url, timeout=30)

    def json(self, system: str, user: str, max_tokens: int = 700) -> dict:
        last = None
        for attempt in range(3):
            try:
                r = self.client.chat.completions.create(
                    model=settings.llm_model, temperature=0, max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
                raw = r.choices[0].message.content or "{}"
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    m = re.search(r"\{.*\}", raw, re.S)
                    if m:
                        return json.loads(m.group(0))
                    raise
            except (RateLimitError, APIConnectionError) as e:
                last = e
                time.sleep(1.5 * (attempt + 1))
            except APIStatusError as e:
                last = e
                if e.status_code < 500:
                    break
                time.sleep(1.5 * (attempt + 1))
            except json.JSONDecodeError as e:
                last = e
        raise LLMError(str(last))

    def text(self, system: str, user: str, max_tokens: int = 300) -> str:
        try:
            r = self.client.chat.completions.create(
                model=settings.llm_model, temperature=0, max_tokens=max_tokens,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            return (r.choices[0].message.content or "").strip()
        except Exception as e:  # noqa: BLE001
            raise LLMError(str(e)) from e
