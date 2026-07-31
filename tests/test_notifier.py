from unittest.mock import Mock

from src.config import Settings
from src.models import Listing
from src.notifier import NtfyNotifier


def settings(tmp_path, topic=None, dry_run=False) -> Settings:
    return Settings(topic, "https://ntfy.sh", dry_run or topic is None, "INFO", 30, tmp_path)


def test_missing_topic_enters_dry_run(tmp_path) -> None:
    notifier = NtfyNotifier(settings(tmp_path))
    assert notifier.settings.dry_run
    assert notifier.send_listing(Listing(name="Couple Room"))


def test_ntfy_retries_on_failure(tmp_path, monkeypatch) -> None:
    session = Mock()
    session.post.side_effect = [Exception("boom"), Mock(status_code=500), Mock(status_code=200)]
    monkeypatch.setattr("time.sleep", lambda _: None)
    notifier = NtfyNotifier(settings(tmp_path, topic="secret-topic"), session=session)
    assert notifier.send_listing(Listing(name="Couple Room", detail_url="https://example.com"))
    assert session.post.call_count == 3


def test_ntfy_failure_returns_false(tmp_path, monkeypatch) -> None:
    session = Mock()
    session.post.return_value = Mock(status_code=500)
    monkeypatch.setattr("time.sleep", lambda _: None)
    notifier = NtfyNotifier(settings(tmp_path, topic="secret-topic"), session=session)
    assert not notifier.send_listing(Listing(name="Couple Room", detail_url="https://example.com"))

