import asyncio
from typing import Final

import aiohttp

PROXY_POOL_API: Final[str] = "http://127.0.0.1:5010/get/"  # 可在config.py中配置
REQUEST_TIMEOUT: Final[aiohttp.ClientTimeout] = aiohttp.ClientTimeout(total=5)


async def get_proxy() -> str | None:
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        try:
            async with session.get(PROXY_POOL_API) as resp:
                if resp.status == 200:
                    proxy = await resp.text()
                    return proxy.strip()
        except Exception:
            return None
    return None


async def get_valid_proxy(
    test_url: str = "https://movie.douban.com/subject/1291543/"
) -> str | None:
    for _ in range(5):  # 最多尝试5次
        proxy = await get_proxy()
        if not proxy:
            await asyncio.sleep(1)
            continue
        # 检查代理可用性
        try:
            async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
                async with session.get(test_url, proxy=f"http://{proxy}") as resp:
                    if resp.status == 200:
                        return proxy
        except Exception:
            pass
        await asyncio.sleep(1)
    return None 
