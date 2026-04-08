"""
数据库迁移脚本 - 添加系统配置和视觉风格字段
"""
from sqlalchemy import create_engine, text
from app.config import get_settings
import json

settings = get_settings()

def run_migration():
    """运行数据库迁移"""
    # 创建数据库连接
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # 1. 创建system_configs表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key VARCHAR(100) UNIQUE NOT NULL,
                value TEXT,
                description VARCHAR(200),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # 2. 为article_categories表添加新字段
        try:
            conn.execute(text("ALTER TABLE article_categories ADD COLUMN visual_style VARCHAR(200)"))
        except:
            pass  # 字段已存在
        
        try:
            conn.execute(text("ALTER TABLE article_categories ADD COLUMN emotion_tone VARCHAR(200)"))
        except:
            pass
        
        try:
            conn.execute(text("ALTER TABLE article_categories ADD COLUMN color_palette VARCHAR(200)"))
        except:
            pass
        
        conn.commit()
        print("Migration completed successfully")

if __name__ == "__main__":
    run_migration()