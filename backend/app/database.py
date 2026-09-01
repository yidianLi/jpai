"""数据库连接：AI库读写 + 原库只读"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

ai_url = (f"mysql+pymysql://{settings.AI_DB_USER}:{settings.AI_DB_PASSWORD}"
          f"@{settings.AI_DB_HOST}:{settings.AI_DB_PORT}/{settings.AI_DB_NAME}?charset=utf8mb4")
ai_engine = create_engine(
    ai_url, pool_size=10, max_overflow=20, pool_recycle=3600,
    pool_pre_ping=True, connect_args={"connect_timeout": 5}, echo=settings.DEBUG,
)
AiSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ai_engine)

src_url = (f"mysql+pymysql://{settings.SOURCE_DB_USER}:{settings.SOURCE_DB_PASSWORD}"
           f"@{settings.SOURCE_DB_HOST}:{settings.SOURCE_DB_PORT}/{settings.SOURCE_DB_NAME}?charset=utf8mb4")
source_engine = create_engine(
    src_url, pool_size=5, max_overflow=10, pool_recycle=3600,
    pool_pre_ping=True, connect_args={"connect_timeout": 5}, echo=False,
)
SourceSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=source_engine)

Base = declarative_base()


def get_ai_db():
    db = AiSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_source_db():
    db = SourceSessionLocal()
    try:
        yield db
    finally:
        db.close()
