from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint, select, func
import datetime

Base = declarative_base()

class Movie(Base):
    __tablename__ = 'movies'
    id = Column(Integer, primary_key=True, autoincrement=False)
    title = Column(String, nullable=False)
    year = Column(String, nullable=True)
    director = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    url = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    update_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC), onupdate=lambda: datetime.datetime.now(datetime.UTC))
    __table_args__ = (UniqueConstraint('url', name='_url_uc'),)

DATABASE_URL = "sqlite+aiosqlite:///./movies.db"
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def add_movie(movie_data):
    async with AsyncSessionLocal() as session:
        async with session.begin():
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

async def get_max_id():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.max(Movie.id)))
        max_id = result.scalar()
        return max_id or 0 