import datetime
from typing import Any, Literal, Sequence

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 异步模型基类。"""

    pass


class Movie(Base):
    __tablename__ = 'movies'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[str | None] = mapped_column(String, nullable=True)
    director: Mapped[str | None] = mapped_column(String, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.UTC)
    )
    update_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
    )
    __table_args__ = (UniqueConstraint('url', name='_url_uc'),)

class SinaUSStock(Base):
    __tablename__ = 'sina_us_stocks'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.UTC)
    )
    update_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
    )
    __table_args__ = (UniqueConstraint('symbol', name='_symbol_uc'),)

DATABASE_URL = "sqlite+aiosqlite:///./movies.db"
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def add_movie(movie_data: dict[str, Any]) -> Literal["success", "duplicate", "fail"]:
    async with AsyncSessionLocal() as session:
        movie = Movie(**movie_data)
        session.add(movie)
        try:
            await session.commit()
            return 'success'
        except Exception as e:
            await session.rollback()
            # 处理唯一约束冲突（重复插入）
            if "UNIQUE constraint failed" in str(e) or "UNIQUE constraint" in str(e):
                return 'duplicate'
            else:
                return 'fail'


async def add_sina_stock(
    stock_data: dict[str, Any]
) -> Literal["success", "duplicate", "fail"]:
    result = await upsert_sina_stocks([stock_data])
    if result["fail"]:
        return "fail"
    if result["success"]:
        return "success"
    return "duplicate"

async def get_max_id() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.max(Movie.id)))
        max_id = result.scalar()
        return max_id or 0


async def upsert_sina_stocks(
    stock_items: Sequence[dict[str, Any]]
) -> dict[str, int]:
    """批量插入或更新新浪股票数据，减少数据库往返次数。"""
    if not stock_items:
        return {"success": 0, "duplicate": 0, "fail": 0}

    normalized: dict[str, dict[str, Any]] = {}
    skipped = 0
    for item in stock_items:
        symbol = item.get("symbol")
        category = item.get("category")
        name = item.get("name")
        if not symbol or not category or not name:
            skipped += 1
            continue
        normalized[symbol] = {"symbol": symbol, "category": category, "name": name}

    if not normalized:
        return {"success": 0, "duplicate": 0, "fail": skipped}

    payload = list(normalized.values())
    symbols = [entry["symbol"] for entry in payload]
    now = datetime.datetime.now(datetime.UTC)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            existing = await session.execute(
                select(SinaUSStock.symbol).where(SinaUSStock.symbol.in_(symbols))
            )
            existing_symbols = set(existing.scalars().all())

            stmt = sqlite_insert(SinaUSStock).values(
                [
                    {
                        "category": entry["category"],
                        "symbol": entry["symbol"],
                        "name": entry["name"],
                        "created_at": now,
                        "update_at": now,
                    }
                    for entry in payload
                ]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[SinaUSStock.symbol],
                set_={
                    "category": stmt.excluded.category,
                    "name": stmt.excluded.name,
                    "update_at": now,
                },
            )
            await session.execute(stmt)

    success_count = len(payload) - len(existing_symbols)
    duplicate_count = len(existing_symbols)
    fail_count = skipped
    return {
        "success": success_count,
        "duplicate": duplicate_count,
        "fail": fail_count,
    }
