import aiohttp
import asyncio
import random

PROXY_POOL_API = "http://127.0.0.1:5010/get/"  # 可在config.py中配置

async def get_proxy():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(PROXY_POOL_API, timeout=5) as resp:
                if resp.status == 200:
                    proxy = await resp.text()
                    return proxy.strip()
        except Exception:
            return None
    return None

async def get_valid_proxy(test_url="https://movie.douban.com/subject/1291543/"):
    for _ in range(5):  # 最多尝试5次
        proxy = await get_proxy()
        if not proxy:
            await asyncio.sleep(1)
            continue
        # 检查代理可用性
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(test_url, proxy=f"http://{proxy}", timeout=5) as resp:
                    if resp.status == 200:
                        return proxy
        except Exception:
            pass
        await asyncio.sleep(1)
    return None 