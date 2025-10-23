import httpx
import asyncio
from bs4 import BeautifulSoup
from crawler.proxy_pool import get_valid_proxy
from crawler.db import add_sina_stock
import random
from fake_useragent import UserAgent
from crawler.config import CONCURRENT_TASKS


async def fetch_sina_us_stock_data(url, use_proxy=True):
    proxy = await get_valid_proxy() if use_proxy else None
    headers = {
        "User-Agent": UserAgent(browsers=['Chrome', 'Edge', 'Firefox', 'Safari', 'Opera']).random,
        "Referer": "https://vip.stock.finance.sina.com.cn/",
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
            return soup
        else:
            print(f"[ERROR] HTTP错误: {url} (status {resp.status_code})")
            return None
    except Exception as e:
        print(f"[ERROR] 异常: {e}")
        return None


def parse_sina_us_stock_data(soup):
    """
    解析新浪美股网站的数据
    :param soup: BeautifulSoup对象
    :return: 包含股票信息的列表
    """
    if not soup:
        return []
    
    stock_data = []
    
    # 查找所有class为col_div的div元素
    col_divs = soup.find_all("div", class_="col_div")
    
    # 第一个col_div没有label，使用"中国"作为category
    if col_divs:
        first_col_div = col_divs[0]
        stocks = first_col_div.find_all("a", href=True)
        for stock in stocks:
            title = stock.get("title", "")
            if title:
                parts = title.split(",")
                if len(parts) >= 3:
                    # 从链接文本中提取名称和股票代码
                    text = stock.get_text()
                    if "(" in text and ")" in text:
                        # 提取括号中的股票代码
                        symbol = text.split("(")[-1].split(")")[0]
                        # 提取括号前的名称
                        name = text.split("(")[0]
                    else:
                        symbol = parts[0]
                        name = parts[2]  # 使用中文名称而不是英文名称
                        # 提取括号中的股票代码
                        if "(" in name and ")" in name:
                            name = name.split("(")[0]
                    stock_data.append({
                        "category": "中国",
                        "symbol": symbol,
                        "name": name
                    })
    
    # 处理其他col_div元素
    for i in range(1, len(col_divs)):
        col_div = col_divs[i]
        # 查找label元素获取category
        label = col_div.find("label")
        category = "未知"
        if label:
            category_text = label.text.strip()
            # 从label文本中提取category
            if "家在美上市" in category_text:
                # 处理"家在美上市XXX:"格式，如"111家在美上市科技类知名公司:"
                category = category_text.split("家在美上市")[1].strip()
                if category.endswith(":"):
                    category = category[:-1]
                # 进一步提取核心类别，如从"科技类知名公司"中提取"科技"
                if "类" in category:
                    category = category.split("类")[0]
            elif "家在美知名" in category_text:
                # 处理"家在美知名XXX:"格式，如"7家在美知名ETF:"
                category = category_text.split("家在美知名")[1].strip()
                if category.endswith(":"):
                    category = category[:-1]
            elif ":" in category_text:
                category = category_text.split(":")[1].strip()
            else:
                category = category_text
        
        # 查找所有股票链接
        stocks = col_div.find_all("a", href=True)
        for stock in stocks:
            title = stock.get("title", "")
            if title:
                parts = title.split(",")
                if len(parts) >= 3:
                    # 从链接文本中提取名称和股票代码
                    text = stock.get_text()
                    if "(" in text and ")" in text:
                        # 提取括号中的股票代码
                        symbol = text.split("(")[-1].split(")")[0]
                        # 提取括号前的名称
                        name = text.split("(")[0]
                    else:
                        symbol = parts[0]
                        name = parts[2]  # 使用中文名称而不是英文名称
                        # 提取括号中的股票代码
                        if "(" in name and ")" in name:
                            name = name.split("(")[0]
                    stock_data.append({
                        "category": category,
                        "symbol": symbol,
                        "name": name
                    })
    
    return stock_data


async def save_sina_us_stock_data(stock_data):
    """
    保存新浪美股数据到数据库
    :param stock_data: 股票数据列表
    :return: 保存结果
    """
    success_count = 0
    duplicate_count = 0
    fail_count = 0
    
    for stock in stock_data:
        result = await add_sina_stock(stock)
        if result == 'success':
            success_count += 1
            print(f"[INFO] 成功保存股票数据: {stock['symbol']} - {stock['name']}")
        elif result == 'duplicate':
            duplicate_count += 1
            print(f"[INFO] 股票数据已存在: {stock['symbol']} - {stock['name']}")
        else:
            fail_count += 1
            print(f"[ERROR] 保存股票数据失败: {stock['symbol']} - {stock['name']}")
    
    print(f"[INFO] 保存完成 - 成功: {success_count}, 重复: {duplicate_count}, 失败: {fail_count}")
    return {
        "success": success_count,
        "duplicate": duplicate_count,
        "fail": fail_count
    }


async def crawl_sina_us_stock(url="https://vip.stock.finance.sina.com.cn/usstock/ustotal.php", use_proxy=True):
    """
    爬取并保存新浪美股数据
    :param url: 爬取的URL
    :param use_proxy: 是否使用代理
    :return: 爬取结果
    """
    print(f"[INFO] 开始爬取新浪美股数据: {url}")
    
    # 获取网页内容
    soup = await fetch_sina_us_stock_data(url, use_proxy)
    if not soup:
        print("[ERROR] 获取网页内容失败")
        return {"status": "failed", "message": "获取网页内容失败"}
    
    # 解析数据
    stock_data = parse_sina_us_stock_data(soup)
    if not stock_data:
        print("[ERROR] 解析数据失败")
        return {"status": "failed", "message": "解析数据失败"}
    
    print(f"[INFO] 解析到 {len(stock_data)} 条股票数据")
    
    # 保存数据
    result = await save_sina_us_stock_data(stock_data)
    
    print("[INFO] 新浪美股数据爬取完成")
    return {
        "status": "success",
        "data_count": len(stock_data),
        "save_result": result
    }