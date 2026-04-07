"""初始化文章创作方向到数据库"""
import json
from app.database import SessionLocal
from app.models.article_category import ArticleCategory
from app.config.article_prompts import ARTICLE_CATEGORIES

def init_article_categories():
    """初始化文章创作方向"""
    db = SessionLocal()
    
    try:
        for name, data in ARTICLE_CATEGORIES.items():
            existing = db.query(ArticleCategory).filter(
                ArticleCategory.name == name
            ).first()
            
            if not existing:
                category = ArticleCategory(
                    name=name,
                    icon=data["icon"],
                    system_prompt=data["system_prompt"],
                    example_topics=json.dumps(data["example_topics"], ensure_ascii=False),
                    image_prompt_template=f"公众号文章配图，主题：{{topic}}，{name}风格，高质量，专业感",
                    is_active=True,
                    sort_order=list(ARTICLE_CATEGORIES.keys()).index(name)
                )
                db.add(category)
                print(f"Added category: {name}")
        
        db.commit()
        print("Article categories initialized successfully")
        
    except Exception as e:
        print(f"Error initializing categories: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_article_categories()