# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述
这是一个异步豆瓣电影爬虫，基于Python asyncio + httpx实现，支持代理IP池、SQLite数据库存储，用于批量抓取豆瓣电影页面信息。

## 架构设计
- **异步框架**: 使用asyncio+httpx实现高并发网络请求
- **数据存储**: SQLAlchemy异步ORM + SQLite数据库
- **代理管理**: 集成代理池API实现IP轮换
- **反爬处理**: User-Agent轮换、请求间隔随机化、异常检测

## 模块结构
```
crawler/
├── config.py      # 全局配置（代理API、并发数）
├── db.py         # 数据库模型和ORM操作
├── crawler.py    # 爬虫核心逻辑（页面抓取+解析）
├── proxy_pool.py # 代理池管理
└── __init__.py
main.py           # 程序入口，命令行参数处理
movies.db         # SQLite数据库文件
```

## 运行命令

### 基本运行
```bash
# 使用默认配置（启用代理池）
uv run python main.py https://movie.douban.com/subject/1291543/

# 批量爬取指定URL
uv run python main.py url1 url2 url3

# 禁用代理池（直连模式）
uv run python main.py https://movie.douban.com/subject/1291543/ --proxy

# 连续爬取100个新页面（从最大ID开始自动递增）
uv run python main.py --count 100
```

### 依赖管理
```bash
# 使用uv安装依赖
uv add httpx[http2] beautifulsoup4 sqlalchemy aiosqlite aiohttp fake-useragent
```

## 关键配置
- **代理池API**: `crawler/proxy_pool.py#L5` - 需部署本地代理池服务
- **并发数**: `crawler/config.py#L2` - 控制asyncio信号量
- **请求超时**: `crawler/crawler.py#L21` - httpx请求超时设置
- **数据库**: `crawler/db.py#L20` - SQLite连接字符串

## 数据库Schema
```sql
movies表结构:
- id (INTEGER PRIMARY KEY): 电影ID（对应豆瓣subject ID）
- title (VARCHAR): 电影标题
- year (VARCHAR): 年份
- director (VARCHAR): 导演
- rating (FLOAT): 评分
- url (VARCHAR UNIQUE): 原始URL
- created_at (DATETIME): 创建时间
- updated_at (DATETIME): 更新时间
```

## 常见操作

### 查看数据库内容
```python
import asyncio
from crawler.db import AsyncSessionLocal
from sqlalchemy import select

async def view_movies():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Movie))
        movies = result.scalars().all()
        for movie in movies:
            print(f"{movie.id}: {movie.title} ({movie.year}) - 评分: {movie.rating}")
```

### 调试单个页面抓取
```python
from crawler.crawler import fetch_movie
import asyncio
result = asyncio.run(fetch_movie("https://movie.douban.com/subject/1291543/", use_proxy=False))
print(result)
```