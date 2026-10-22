"""Checks run on the LLM answer before it is returned."""
import re

_NUM = r"(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?"
_CUR_BEFORE = re.compile(rf"(?:US\$|\$|USD\s?|€|£|EUR\s?)\s?{_NUM}\s?([kK])?\b")
_CUR_AFTER = re.compile(rf"{_NUM}\s?(?:USD|US dollars|dollars|euros|EUR)\b", re.I)
_ANY_NUM = re.compile(rf"{_NUM}")


def _val(whole: str, frac: str | None, k: str | None = None) -> float:
    v = float(whole.replace(",", "") + (frac or ""))
    return v * 1000 if k else v


def amounts(text: str) -> set[float]:
    """All currency amounts in the text as numbers ($18,995, 18995 USD and $18995 are the same)."""
    out = set()
    for m in _CUR_BEFORE.finditer(text):
        out.add(_val(m.group(1), m.group(2), m.group(3)))
    for m in _CUR_AFTER.finditer(text):
        out.add(_val(m.group(1), m.group(2)))
    return out


def numbers(text: str) -> set[float]:
    return {_val(m.group(1), m.group(2)) for m in _ANY_NUM.finditer(text)}


def check_prices(answer: str, context: str, user_amounts: set[float] | None = None,
                 verdict: str = "none") -> list[str]:
    """Return a list of problems (empty means fine).
    1) every amount in the answer must literally exist in the retrieved context (except numbers the user themselves quoted);
    2) if the user quoted a price the sources don't contain, the bot may not 'support' it."""
    problems = []
    ctx_nums = numbers(context)
    for a in amounts(answer):
        if a not in ctx_nums and a not in (user_amounts or set()):   # repeating the user's own number to correct it is allowed
            problems.append(f"amount {a:g} is not in the sources")
    for u in (user_amounts or set()):
        if u not in ctx_nums and verdict == "supported":
            problems.append(f"user-claimed amount {u:g} is not in the sources but was confirmed")
    return problems
