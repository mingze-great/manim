from app.database import SessionLocal, engine, Base
from app.models.template_category import TemplateCategory
from app.models.template import Template


def migrate():
    print("Migrating template categories...")
    
    Base.metadata.create_all(bind=engine, tables=[TemplateCategory.__table__])
    
    db = SessionLocal()
    
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(templates)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'category_id' not in columns:
                conn.execute(text("ALTER TABLE templates ADD COLUMN category_id INTEGER"))
                conn.commit()
                print("Added category_id column to templates table")
            else:
                print("category_id column already exists")
        
        category_map = {}
        for cat in db.query(TemplateCategory).all():
            category_map[cat.code] = cat.id
        
        templates = db.query(Template).filter(Template.category.isnot(None)).all()
        
        updated = 0
        for template in templates:
            if template.category and template.category in category_map:
                template.category_id = category_map[template.category]
                updated += 1
        
        db.commit()
        print(f"Updated {updated} templates with category_id")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("Migration completed!")


if __name__ == "__main__":
    migrate()
