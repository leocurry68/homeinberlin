from __future__ import annotations

import logging
import time
from datetime import datetime

import requests

from .config import BERLIN_TZ, Settings
from .models import Listing

LOGGER = logging.getLogger(__name__)


def masked_topic(topic: str | None) -> str:
    if not topic:
        return "<unset>"
    if len(topic) <= 6:
        return "***"
    return f"{topic[:3]}...{topic[-3:]}"


class NtfyNotifier:
    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        self.settings = settings
        self.session = session or requests.Session()

    def format_listing_message(self, listing: Listing) -> str:
        return f"""🏠 Wedding 出现新的双人房

名称：{listing.name}
类型：{listing.listing_type}
地址：{listing.address}
区域：{listing.area}
邮编：{listing.postal_code}
房间：{listing.rooms}
入住人数：{listing.max_occupancy}
面积：{listing.size}
月租：{listing.monthly_rent}
其他费用：{listing.other_costs}
押金：{listing.deposit}
可入住日期：{listing.available_from}

双人入住匹配原因：
{listing.two_person_reason}

Wedding 匹配原因：
{listing.wedding_reason}

立即查看：
{listing.detail_url}"""

    def send_listing(self, listing: Listing, force: bool = False) -> bool:
        message = self.format_listing_message(listing)
        if self.settings.dry_run and not force:
            print(message)
            return True
        if not self.settings.ntfy_url:
            LOGGER.info("ntfy topic is not configured; dry-run only (%s)", masked_topic(self.settings.ntfy_topic))
            print(message)
            return True
        headers = {
            "Title": "Home in Berlin 新双人房",
            "Priority": "high",
            "Tags": "house,bell",
            "Click": listing.detail_url,
        }
        return self._post(message, headers)

    def send_test(self) -> bool:
        listing = Listing(name="ntfy 测试通知", detail_url="https://home-in-berlin.de/")
        return self.send_listing(listing, force=True)

    def send_error(self, error_type: str, message: str, page_url: str) -> bool:
        body = f"""错误类型：{error_type}
简要错误信息：{message}
发生时间：{datetime.now(BERLIN_TZ).isoformat()}
访问页面：{page_url}
建议检查内容：检查网站访问、页面结构、GitHub Actions 日志和本地状态文件。"""
        if self.settings.dry_run or not self.settings.ntfy_url:
            LOGGER.error("Monitor error: %s - %s", error_type, message)
            return False
        return self._post(body, {"Title": "Home in Berlin 监控异常", "Priority": "high", "Tags": "warning"})

    def _post(self, body: str, headers: dict[str, str]) -> bool:
        assert self.settings.ntfy_url is not None
        for attempt in range(1, 4):
            try:
                response = self.session.post(self.settings.ntfy_url, data=body.encode("utf-8"), headers=headers, timeout=30)
                if 200 <= response.status_code < 300:
                    return True
                LOGGER.warning("ntfy request failed with HTTP %s", response.status_code)
            except Exception as exc:
                LOGGER.warning("ntfy request failed: %s", exc)
            time.sleep(2**attempt)
        return False
