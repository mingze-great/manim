from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from app.config import get_settings

settings = get_settings()

# 根据数据库类型配置引擎
if settings.DATABASE_URL.startswith("postgresql"):
    # PostgreSQL 配置
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # 连接健康检查
        pool_recycle=3600,   # 每小时回收连接
        echo=settings.DEBUG if hasattr(settings, 'DEBUG') else False
    )
else:
    # SQLite 配置（向后兼容）
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG if hasattr(settings, 'DEBUG') else False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# SQLite 性能优化
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite 性能优化：启用外键约束"""
    if "sqlite" in str(settings.DATABASE_URL):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
