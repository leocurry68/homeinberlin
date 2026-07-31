from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

from .config import BERLIN_TZ
from .models import Listing

LOGGER = logging.getLogger(__name__)


class JsonStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.seen_path = data_dir / "seen_listings.json"
        self.active_path = data_dir / "active_listings.json"
        self.error_path = data_dir / "error_state.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for path in [self.seen_path, self.active_path, self.error_path]:
            if not path.exists():
                self.write_json(path, {})

    def load_json(self, path: Path, default: object) -> object:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("State file %s is unreadable; recovering with empty state: %s", path, exc)
            return default

    def write_json(self, path: Path, data: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
                json.dump(data, tmp, ensure_ascii=False, indent=2, sort_keys=True)
                tmp.write("\n")
                tmp_path = Path(tmp.name)
            os.replace(tmp_path, path)
        except OSError:
            LOGGER.exception("Could not write state file %s", path)
            raise

    def load_seen(self) -> dict[str, dict[str, object]]:
        data = self.load_json(self.seen_path, {})
        return data if isinstance(data, dict) else {}

    def load_active(self) -> dict[str, dict[str, object]]:
        data = self.load_json(self.active_path, {})
        return data if isinstance(data, dict) else {}

    def save_active(self, listings: list[Listing]) -> None:
        self.write_json(self.active_path, {item.unique_id(): item.to_dict() for item in listings})

    def mark_notified(self, listing: Listing) -> None:
        seen = self.load_seen()
        seen[listing.unique_id()] = {
            "last_notified_at": datetime.now(BERLIN_TZ).isoformat(),
            "listing": listing.to_dict(),
        }
        self.write_json(self.seen_path, seen)

    def new_or_reappeared(self, listings: list[Listing]) -> list[Listing]:
        active = self.load_active()
        return [item for item in listings if item.unique_id() not in active]

    def error_allowed(self, error_type: str) -> bool:
        state = self.load_json(self.error_path, {})
        if not isinstance(state, dict):
            state = {}
        raw = state.get(error_type)
        if not isinstance(raw, str):
            return True
        try:
            last = datetime.fromisoformat(raw)
        except ValueError:
            return True
        return datetime.now(BERLIN_TZ) - last >= timedelta(hours=24)

    def mark_error_sent(self, error_type: str) -> None:
        state = self.load_json(self.error_path, {})
        if not isinstance(state, dict):
            state = {}
        state[error_type] = datetime.now(BERLIN_TZ).isoformat()
        self.write_json(self.error_path, state)

    def reset(self) -> None:
        self.write_json(self.seen_path, {})
        self.write_json(self.active_path, {})
        self.write_json(self.error_path, {})
