from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS_PREFIXES = ("utm_",)
TRACKING_PARAMS_EXACT = {"fbclid", "gclid", "yclid", "mc_cid", "mc_eid"}


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    query = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        if k in TRACKING_PARAMS_EXACT or any(k.startswith(p) for p in TRACKING_PARAMS_PREFIXES):
            continue
        query.append((k, v))
    cleaned = parsed._replace(query=urlencode(query), fragment="", netloc=parsed.netloc.lower())
    result = urlunparse(cleaned)
    return result[:-1] if result.endswith("/") else result


def text_similarity(a: str, b: str) -> float:
    a_clean = re.sub(r"\s+", " ", a.lower()).strip()
    b_clean = re.sub(r"\s+", " ", b.lower()).strip()
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def robust_json_loads(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])
