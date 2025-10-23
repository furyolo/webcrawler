import argparse
import asyncio
from crawler.crawler import batch_fetch
from crawler.db import init_db, get_max_id
from crawler.sina_us_stock import crawl_sina_us_stock
import sys

async def main():
    parser = argparse.ArgumentParser(description="Douban Movie Crawler and Sina US Stock Crawler")
    parser.add_argument('urls', nargs='*', help='Movie page URLs')
    parser.add_argument('--proxy', action='store_true', help='Enable proxy pool (default: no proxy)')
    parser.add_argument('--count', type=int, default=100, help='Number of sequential new URLs to crawl')
    parser.add_argument('--sina-us-stock', action='store_true', help='Crawl Sina US stock data')
    parser.add_argument('--sina-url', default='https://vip.stock.finance.sina.com.cn/usstock/ustotal.php', help='URL for Sina US stock data')
    args = parser.parse_args()

    await init_db()
    use_proxy = args.proxy

    # 如果指定了--sina-us-stock参数，则爬取新浪美股数据
    if args.sina_us_stock:
        result = await crawl_sina_us_stock(args.sina_url, use_proxy=use_proxy)
        print(f"[INFO] 新浪美股数据爬取结果: {result}")
        return

    # 否则执行原有的豆瓣电影爬取逻辑
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
