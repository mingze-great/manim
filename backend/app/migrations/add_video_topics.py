from app.database import engine, Base
from app.models.video_topic_category import VideoTopicCategory
from sqlalchemy import text


def migrate():
    """添加 video_topic_categories 表和 Project.category 字段"""
    
    print("Starting migration...")
    
    Base.metadata.create_all(bind=engine, tables=[VideoTopicCategory.__table__])
    
    print("Created video_topic_categories table")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(projects)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'category' not in columns:
                conn.execute(text("ALTER TABLE projects ADD COLUMN category VARCHAR(50)"))
                conn.commit()
                print("Added category column to projects table")
            else:
                print("category column already exists in projects table")
                
    except Exception as e:
        print(f"Note: {e}")
    
    print("\nMigration completed successfully!")


if __name__ == "__main__":
    migrate()