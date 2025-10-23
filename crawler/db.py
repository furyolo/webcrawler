import datetime
from typing import Any, Literal

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, func, select
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
    async with AsyncSessionLocal() as session:
        # 首先尝试插入新数据
        stock = SinaUSStock(**stock_data)
        session.add(stock)
        try:
            await session.commit()
            return 'success'
        except Exception as e:
            await session.rollback()
            # 处理唯一约束冲突（重复插入）
            if "UNIQUE constraint failed" in str(e) or "UNIQUE constraint" in str(e):
                # 如果是唯一约束冲突，尝试更新现有数据
                try:
                    result = await session.execute(
                        select(SinaUSStock).where(SinaUSStock.symbol == stock_data['symbol'])
                    )
                    existing_stock = result.scalar_one_or_none()
                    if existing_stock:
                        # 更新现有数据
                        existing_stock.category = stock_data['category']
                        existing_stock.name = stock_data['name']
                        existing_stock.update_at = datetime.datetime.now(datetime.UTC)
                        await session.commit()
                        return 'duplicate'  # 表示数据已存在但已更新
                    else:
                        return 'fail'
                except Exception as update_e:
                    await session.rollback()
                    print(f"[ERROR] 更新股票数据失败: {stock_data['symbol']} - {update_e}")
                    return 'fail'
            else:
                return 'fail'

async def get_max_id() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.max(Movie.id)))
        max_id = result.scalar()
        return max_id or 0
