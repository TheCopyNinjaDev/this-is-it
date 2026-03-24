from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx


LOGGER = logging.getLogger(__name__)

PROXY_BLOCK_RE = re.compile(
    r"(?P<label>.+?):\s*"
    r"(?:\r?\n)+IP:\s*(?P<host>[^\s]+)\s*"
    r"(?:\r?\n)+Порт http\(s\)/socks5:\s*(?P<http_port>\d+)\s*/\s*(?P<socks5_port>\d+)\s*"
    r"(?:\r?\n)+Логин:\s*(?P<username>[^\r\n]+)\s*"
    r"(?:\r?\n)+Пароль:\s*(?P<password>[^\r\n]+)",
    re.MULTILINE,
)


@dataclass(slots=True)
class ProxyEndpoint:
    label: str
    host: str
    http_port: int
    socks5_port: int
    username: str
    password: str

    @property
    def display_name(self) -> str:
        return self.label.strip() or self.host

    def url(self, proxy_type: str) -> str:
        scheme = "socks5" if proxy_type.lower().startswith("socks") else "http"
        port = self.socks5_port if scheme == "socks5" else self.http_port
        username = quote(self.username, safe="")
        password = quote(self.password, safe="")
        return f"{scheme}://{username}:{password}@{self.host}:{port}"

    def short(self, proxy_type: str) -> str:
        port = self.socks5_port if proxy_type.lower().startswith("socks") else self.http_port
        scheme = "socks5" if proxy_type.lower().startswith("socks") else "http"
        return f"{self.display_name} [{scheme} {self.host}:{port}]"


def parse_proxy_source(raw_text: str) -> list[ProxyEndpoint]:
    text = raw_text.strip()
    if not text:
        return []

    matches = list(PROXY_BLOCK_RE.finditer(text))
    if matches:
        return [
            ProxyEndpoint(
                label=match.group("label").strip(),
                host=match.group("host").strip(),
                http_port=int(match.group("http_port")),
                socks5_port=int(match.group("socks5_port")),
                username=match.group("username").strip(),
                password=match.group("password").strip(),
            )
            for match in matches
        ]

    proxies: list[ProxyEndpoint] = []
    for index, line in enumerate(text.splitlines(), start=1):
        candidate = line.strip()
        if not candidate:
            continue
        if "://" in candidate:
            parsed = httpx.URL(candidate)
            if parsed.host is None or parsed.port is None or parsed.username is None or parsed.password is None:
                raise ValueError(f"Прокси в строке {index} должен содержать host, port, login и password")
            proxies.append(
                ProxyEndpoint(
                    label=f"Proxy {index}",
                    host=parsed.host,
                    http_port=parsed.port,
                    socks5_port=parsed.port,
                    username=parsed.username,
                    password=parsed.password,
                )
            )
            continue

        parts = candidate.split(":", 3)
        if len(parts) != 4:
            raise ValueError(f"Не удалось распознать прокси в строке {index}")
        host, port_text, username, password = parts
        if not port_text.isdigit():
            raise ValueError(f"Некорректный порт в строке {index}")
        port = int(port_text)
        proxies.append(
            ProxyEndpoint(
                label=f"Proxy {index}",
                host=host.strip(),
                http_port=port,
                socks5_port=port,
                username=username.strip(),
                password=password.strip(),
            )
        )

    return proxies


class ProxyPool:
    def __init__(
        self,
        *,
        proxy_type: str,
        storage_path: Path,
        probe_url: str,
        initial_proxy: str | None = None,
    ) -> None:
        self.proxy_type = proxy_type
        self.storage_path = storage_path
        self.probe_url = probe_url
        self.initial_proxy = initial_proxy
        self._entries: list[ProxyEndpoint] = []
        self._active_index: int | None = None
        self._lock = asyncio.Lock()

    @property
    def has_entries(self) -> bool:
        return bool(self._entries)

    @property
    def active(self) -> ProxyEndpoint | None:
        if self._active_index is None:
            return None
        if self._active_index >= len(self._entries):
            return None
        return self._entries[self._active_index]

    @property
    def active_proxy_url(self) -> str | None:
        active = self.active
        if active is None:
            return None
        return active.url(self.proxy_type)

    async def load(self) -> None:
        raw_text: str | None = None
        if self.storage_path.exists():
            raw_text = self.storage_path.read_text(encoding="utf-8")
        elif self.initial_proxy:
            raw_text = self.initial_proxy

        if not raw_text:
            return

        entries = parse_proxy_source(raw_text)
        async with self._lock:
            self._entries = entries
            self._active_index = 0 if entries else None

        await self.ensure_active_proxy()

    async def ensure_active_proxy(self) -> ProxyEndpoint | None:
        async with self._lock:
            if not self._entries:
                self._active_index = None
                return None
            start_index = self._active_index or 0

        selected = await self._find_working_proxy(start_index=start_index)
        if selected is not None:
            return selected

        async with self._lock:
            if self._entries:
                self._active_index = start_index
                return self._entries[start_index]
            self._active_index = None
            return None

    async def install_from_text(self, raw_text: str) -> tuple[ProxyEndpoint, int]:
        entries = parse_proxy_source(raw_text)
        if not entries:
            raise ValueError("Файл не содержит ни одного прокси")

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(raw_text.strip() + "\n", encoding="utf-8")

        async with self._lock:
            self._entries = entries
            self._active_index = 0

        await self._find_working_proxy(start_index=0)

        async with self._lock:
            active = self._entries[self._active_index if self._active_index is not None else 0]

        return active, len(entries)

    async def rotate_after_failure(self) -> ProxyEndpoint | None:
        async with self._lock:
            if not self._entries:
                return None
            start_index = 0 if self._active_index is None else (self._active_index + 1) % len(self._entries)

        return await self._find_working_proxy(start_index=start_index)

    async def _find_working_proxy(self, *, start_index: int) -> ProxyEndpoint | None:
        async with self._lock:
            entries = list(self._entries)

        if not entries:
            return None

        for offset in range(len(entries)):
            index = (start_index + offset) % len(entries)
            entry = entries[index]
            if await self._probe(entry):
                async with self._lock:
                    self._active_index = index
                return entry
        return None

    async def _probe(self, entry: ProxyEndpoint) -> bool:
        proxy_url = entry.url(self.proxy_type)
        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=10.0, follow_redirects=True) as client:
                response = await client.get(self.probe_url)
                response.raise_for_status()
                payload = response.json()
                return bool(payload.get("ok"))
        except Exception as error:
            LOGGER.warning("Telegram proxy probe failed for %s: %s", entry.short(self.proxy_type), error)
            return False
