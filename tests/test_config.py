from src.config import normalize_ntfy_topic


def test_normalize_ntfy_topic_accepts_plain_topic() -> None:
    assert normalize_ntfy_topic("shaokun-wedding-abc") == "shaokun-wedding-abc"


def test_normalize_ntfy_topic_accepts_ntfy_url() -> None:
    assert normalize_ntfy_topic("https://ntfy.sh/shaokun-wedding-abc") == "shaokun-wedding-abc"


def test_normalize_ntfy_topic_accepts_publish_url() -> None:
    assert normalize_ntfy_topic("https://ntfy.sh/shaokun-wedding-abc/publish?message=hello") == "shaokun-wedding-abc"

