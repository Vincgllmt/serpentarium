import socket

from zeroconf import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

HOSTNAME = "serpentarium.local."
SERVICE_NAME = "Serpentarium._http._tcp.local."

_aiozc: AsyncZeroconf | None = None
_info: ServiceInfo | None = None


def _local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


async def start_mdns(port: int = 5173) -> None:
    global _aiozc, _info

    _info = ServiceInfo(
        "_http._tcp.local.",
        SERVICE_NAME,
        addresses=[socket.inet_aton(_local_ip())],
        port=port,
        server=HOSTNAME,
    )
    _aiozc = AsyncZeroconf()
    await _aiozc.async_register_service(_info)


async def stop_mdns() -> None:
    global _aiozc, _info
    if _aiozc and _info:
        await _aiozc.async_unregister_service(_info)
        await _aiozc.async_close()
    _aiozc = None
    _info = None
