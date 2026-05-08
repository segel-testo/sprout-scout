import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

REDIRECT_STATUSES = {301, 302, 303, 307, 308}
MAX_REDIRECTS = 5


def _ip_blocked(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


async def _resolve_safe(host: str) -> bool:
    loop = asyncio.get_event_loop()
    try:
        infos = await loop.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        addr = info[4][0]
        if _ip_blocked(addr):
            return False
    return True


async def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return not _ip_blocked(host)
    except ValueError:
        pass
    return await _resolve_safe(host)


async def _walk(client: httpx.AsyncClient, url: str, method: str) -> httpx.Response | None:
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        if not await is_safe_url(current):
            return None
        try:
            response = await client.request(method, current)
        except Exception:
            return None
        if response.status_code in REDIRECT_STATUSES:
            location = response.headers.get("location")
            if not location:
                return response
            current = urljoin(current, location)
            continue
        return response
    return None


async def safe_get(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    return await _walk(client, url, "GET")


async def safe_head(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    return await _walk(client, url, "HEAD")
