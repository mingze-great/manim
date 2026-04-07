#!/usr/bin/env python3
"""
从 SQLite 迁移数据到 PostgreSQL
"""
import sqlite3
import os
import sys

def migrate_database(sqlite_path, postgres_url):
    """
    迁移数据从 SQLite 到 PostgreSQL
    
    注意：这个脚本需要在 Docker 容器内运行
    """
    import psycopg2
    from psycopg2.extras import execute_values
    
    print(f"📦 开始迁移数据...")
    print(f"源数据库: {sqlite_path}")
    print(f"目标数据库: PostgreSQL")
    
    # 连接数据库
    sqlite_conn = sqlite3.connect(sqlite_path)
    postgres_conn = psycopg2.connect(postgres_url)
    
    # 获取所有表
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    
    print(f"\n找到 {len(tables)} 个表需要迁移")
    
    for table in tables:
        table_name = table[0]
        print(f"\n迁移表: {table_name}")
        
        # 读取 SQLite 数据
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"  表 {table_name} 无数据，跳过")
            continue
        
        # 获取列名
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"  列: {', '.join(columns)}")
        print(f"  行数: {len(rows)}")
        
        # 插入到 PostgreSQL
        pg_cursor = postgres_conn.cursor()
        
        # 使用 INSERT ... ON CONFLICT DO NOTHING 避免重复
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)
        
        try:
            execute_values(
                pg_cursor,
                f"INSERT INTO {table_name} ({columns_str}) VALUES %s ON CONFLICT DO NOTHING",
                rows
            )
            postgres_conn.commit()
            print(f"  ✅ 成功迁移 {len(rows)} 行")
        except Exception as e:
            postgres_conn.rollback()
            print(f"  ❌ 迁移失败: {e}")
        
        pg_cursor.close()
    
    # 关闭连接
    sqlite_conn.close()
    postgres_conn.close()
    
    print("\n✅ 数据迁移完成！")


if __name__ == "__main__":
    # 默认路径
    SQLITE_PATH = "/app/data/manim.db"  # Docker 容器内的路径
    POSTGRES_URL = os.environ.get("DATABASE_URL", "")
    
    if not POSTGRES_URL:
        print("❌ 错误: 请设置 DATABASE_URL 环境变量")
        sys.exit(1)
    
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ 错误: SQLite 数据库不存在: {SQLITE_PATH}")
        sys.exit(1)
    
    migrate_database(SQLITE_PATH, POSTGRES_URL)
