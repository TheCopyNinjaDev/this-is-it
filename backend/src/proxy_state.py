from __future__ import annotations

_proxy_urls: list[str | None] = []


def get_proxy_urls() -> list[str | None]:
    if _proxy_urls:
        return list(_proxy_urls)
    from src.config.settings import settings
    return [settings.TELEGRAM_PROXY_URL]


def set_proxy_urls(urls: list[str]) -> None:
    global _proxy_urls
    _proxy_urls = list(urls) if urls else []
