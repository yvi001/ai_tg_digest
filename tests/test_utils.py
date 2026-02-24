from ai_tg_digest.utils import normalize_url, robust_json_loads, text_similarity


def test_normalize_url_removes_tracking():
    url = "https://example.com/x?utm_source=tg&gclid=abc&id=42#frag"
    assert normalize_url(url) == "https://example.com/x?id=42"


def test_similarity_threshold_behavior():
    a = "OpenAI выпустила новую модель для кода"
    b = "OpenAI представила новую модель для программирования"
    c = "Курс валют вырос на рынке"
    assert text_similarity(a, b) > text_similarity(a, c)


def test_robust_json_loads_with_wrapper_text():
    raw = "Result:\n```json\n{\"x\": 1}\n```"
    assert robust_json_loads(raw)["x"] == 1
