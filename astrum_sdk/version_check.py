"""Разовая (за процесс) проверка новой версии SDK на GitHub.

Best-effort: любая ошибка (нет сети, GitHub недоступен, таймаут) молча
игнорируется — эта проверка никогда не должна мешать работе SDK или
бросать исключения.
"""

import json
import logging
import urllib.request

from .version import __version__

logger = logging.getLogger("astrum_sdk")

_RELEASES_URL = "https://api.github.com/repos/AstrumDe/sdk-python/releases/latest"
_already_checked = False


def check_for_updates(timeout: float = 1.5) -> None:
    global _already_checked
    if _already_checked:
        return
    _already_checked = True
    try:
        req = urllib.request.Request(
            _RELEASES_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "astrum-sdk-python"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.load(response)
        latest = str(data.get("tag_name", "")).lstrip("v")
        if latest and latest != __version__:
            logger.warning(
                "Доступна новая версия astrum-sdk: %s (у вас установлена %s). "
                "Обновление: https://github.com/AstrumDe/sdk-python/releases/tag/v%s",
                latest, __version__, latest,
            )
    except Exception:
        pass
