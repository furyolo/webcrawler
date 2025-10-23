import argparse
import asyncio
from crawler.crawler import batch_fetch
from crawler.db import init_db, get_max_id
import sys

async def main():
    parser = argparse.ArgumentParser(description="Douban Movie Crawler")
    parser.add_argument('urls', nargs='*', help='Movie page URLs')
    parser.add_argument('--proxy', action='store_true', help='Enable proxy pool (default: no proxy)')
    parser.add_argument('--count', type=int, default=100, help='Number of sequential new URLs to crawl')
    args = parser.parse_args()

    await init_db()
    use_proxy = args.proxy

    if args.urls:
        urls = args.urls
    else:
        # 自动批量生成新URL
        max_id = await get_max_id()
        urls = [f"https://movie.douban.com/subject/{max_id + i + 1}/" for i in range(args.count)]
        print(f"[INFO] 当前最大id: {max_id}，即将爬取: {urls}")
    results = await batch_fetch(urls, use_proxy=use_proxy)

if __name__ == "__main__":
    asyncio.run(main())
