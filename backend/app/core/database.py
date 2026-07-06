from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = "mysql+pymysql://root:123456@vip.bj.frp.one:46403/private_ops_copilot"

engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,        # 每次取连接前ping MySQL，失效自动重建连接（解决2013核心参数）
    pool_recycle=180,          # 3分钟强制回收闲置连接，远小于MySQL默认8小时超时
    pool_size=8,               # 连接池基础数量，远程不要开太大
    max_overflow=12,           # 最大临时溢出连接
    pool_timeout=10            # 等待可用连接超时10秒，避免卡死
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()