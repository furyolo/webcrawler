# Douban Movie Crawler & Sina US Stock Crawler

## 项目简介
本项目为异步批量爬取豆瓣电影页面（如《功夫》）和新浪美股网站的爬虫，支持代理IP池、SQLite数据库存储，基于httpx+SQLAlchemy异步ORM实现。

## 依赖安装
```bash
uv add httpx[http2] beautifulsoup4 sqlalchemy aiosqlite aiohttp
```

## 代理池要求
需本地或远程部署[jhao104/proxy_pool](https://github.com/jhao104/proxy_pool)或兼容API，默认API地址为`http://127.0.0.1:5010/get/`，可在`config.py`中修改。

## 配置说明
- `config.py`：可配置代理池API、User-Agent池、并发数等参数。

## 数据库说明
- 使用SQLite，数据库文件为`movies.db`，表结构见`db.py`。

## 运行方法
### 豆瓣电影单页爬取
```bash
uv run main.py https://movie.douban.com/subject/1291543/
```

### 豆瓣电影批量爬取
```bash
uv run main.py url1 url2 url3 ...
```

### 关闭代理池（直连模式）
```bash
uv run main.py https://movie.douban.com/subject/1291543/ --proxy
```

### 新浪美股数据爬取
```bash
uv run main.py --sina-us-stock
```

### 新浪美股数据爬取（指定URL）
```bash
uv run main.py --sina-us-stock --sina-url "https://vip.stock.finance.sina.com.cn/usstock/ustotal.php"
```

## 命令行参数说明
- `urls`：待爬取的电影页面URL列表，支持多个
- `--proxy`：启用代理池；默认使用直连模式
- `--sina-us-stock`：爬取新浪美股数据
- `--sina-url`：指定新浪美股数据的URL（默认为https://vip.stock.finance.sina.com.cn/usstock/ustotal.php）

## 主要文件说明
- `main.py`：程序入口，批量调度
- `crawler.py`：豆瓣电影爬虫主逻辑，异步并发
- `sina_us_stock.py`：新浪美股爬虫主逻辑
- `db.py`：数据库ORM模型与操作
- `proxy_pool.py`：代理池API集成
- `config.py`：全局配置

## 注意事项
- 豆瓣有反爬机制，建议合理设置并发数与请求间隔
- 代理池需保证高可用性，否则爬取效率受影响
- 仅供学习与研究使用，请勿用于非法用途
