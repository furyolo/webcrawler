import httpx
import asyncio
from bs4 import BeautifulSoup
from crawler.proxy_pool import get_valid_proxy
from crawler.db import add_movie
import random
from fake_useragent import UserAgent
from crawler.config import CONCURRENT_TASKS
import re

async def fetch_movie(url, use_proxy=True):
    proxy = await get_valid_proxy() if use_proxy else None
    headers = {
        "User-Agent": UserAgent(browsers=['Chrome', 'Edge', 'Firefox', 'Safari', 'Opera']).random,
        "Referer": "https://movie.douban.com/",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }
    try:
        if proxy:
            async with httpx.AsyncClient(proxy=f"http://{proxy}", timeout=20) as client:
                resp = await client.get(url, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # 检查是否被豆瓣安全拦截
            if '有异常请求从你的 IP 发出' in resp.text or 'sec.douban.com' in resp.text:
                print(f"[ERROR] 有异常请求从你的 IP 发出，请 登录 使用豆瓣: {url}")
                return None
            # 解析字段
            title = soup.find("span", property="v:itemreviewed")
            year = soup.find("span", class_="year")
            director = soup.find("a", rel="v:directedBy")
            rating = soup.find("strong", class_="ll rating_num", property="v:average")
            # 提取URL中的id
            match = re.search(r"subject/(\d+)(/|$)", url)
            url_id = match.group(1) if match else None
            movie_data = {
                "id": int(url_id) if url_id else None,
                "title": title.text.strip() if title else None,
                "year": year.text.strip("() ") if year else None,
                "director": director.text.strip() if director else None,
                "rating": float(rating.text.strip()) if rating and rating.text.strip() else None,
                "url": url
            }
            if not all([movie_data["id"], movie_data["title"], movie_data["year"], movie_data["director"]]):
                print(f"[DEBUG] Parsed data missing fields: {movie_data}")
                print(f"[DEBUG] Response text (first 500 chars): {resp.text[:500]}")
                return None
            result = await add_movie(movie_data)
            if result == 'success':
                print(f"[INFO] 插入成功: {movie_data['id']} {movie_data['title']}")
            elif result == 'duplicate':
                print(f"[INFO] 重复插入: {movie_data['id']} {movie_data['title']}")
            else:
                print(f"[ERROR] 插入失败: {movie_data['id']} {movie_data['title']}")
            return movie_data
        elif resp.status_code == 404 or resp.status_code == 302:
            # 检查是否跳转到 sec.douban.com
            location = resp.headers.get('location', '')
            if 'sec.douban.com' in location:
                print(f"[ERROR] 有异常请求从你的 IP 发出，请 登录 使用豆瓣")
                return None
            print(f"[WARN] 页面不存在: {url}")
            return 'not_found'
        elif resp.status_code in (403, 418):
            print(f"[WARN] 被禁止/反爬: {url} (status {resp.status_code})")
            return None
        else:
            print(f"[ERROR] 未知HTTP错误: {url} (status {resp.status_code})")
            print(f"[DEBUG] Response text (first 500 chars): {resp.text[:500]}")
            return None
    except Exception as e:
        print(f"[DEBUG] Exception: {e}")
        return None

async def batch_fetch(urls, delay=1, use_proxy=True, max_retries=3):
    sem = asyncio.Semaphore(CONCURRENT_TASKS)
    results = [None] * len(urls)
    async def sem_fetch(url, idx):
        for attempt in range(1, max_retries + 1):
            async with sem:
                movie = await fetch_movie(url, use_proxy=use_proxy)
                if movie and movie != 'not_found':
                    results[idx] = movie
                    break
                elif movie == 'not_found':
                    results[idx] = None
                    break
                else:
                    print(f"[ERROR] Failed to fetch: {url} (attempt {attempt}/{max_retries})")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
        if not results[idx] and (movie != 'not_found'):
            print(f"[ERROR] Final fail: {url}")
        await asyncio.sleep(delay + random.uniform(0, 1))
        return results[idx]
    tasks = [sem_fetch(url, idx) for idx, url in enumerate(urls)]
    await asyncio.gather(*tasks)
    return results 