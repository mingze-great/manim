"""
初始化默认封面风格数据
"""
from app.database import SessionLocal
from app.models.cover_style import CoverStyle


DEFAULT_COVER_STYLES = [
    {
        "name": "简约商务",
        "description": "适合职场、商业、知识类内容",
        "base_prompt": "公众号封面，主题：{topic}，简约商务风格，专业感，高质量，无文字，9:16比例",
        "font_recommendation": "黑体",
        "color_recommendation": "#333333",
        "is_active": True,
    },
    {
        "name": "文艺清新",
        "description": "适合情感、生活、文艺类内容",
        "base_prompt": "公众号封面，主题：{topic}，文艺清新风格，柔和色调，意境感，高质量，无文字，9:16比例",
        "font_recommendation": "宋体",
        "color_recommendation": "#5B5B5B",
        "is_active": True,
    },
    {
        "name": "科技感",
        "description": "适合科技、互联网、创新类内容",
        "base_prompt": "公众号封面，主题：{topic}，科技感风格，蓝色调，未来感，高质量，无文字，9:16比例",
        "font_recommendation": "黑体",
        "color_recommendation": "#1E90FF",
        "is_active": True,
    },
    {
        "name": "时尚潮流",
        "description": "适合时尚、潮流、年轻化内容",
        "base_prompt": "公众号封面，主题：{topic}，时尚潮流风格，活力色彩，现代感，高质量，无文字，9:16比例",
        "font_recommendation": "黑体",
        "color_recommendation": "#FF6B6B",
        "is_active": True,
    },
    {
        "name": "学术专业",
        "description": "适合学术、教育、专业领域内容",
        "base_prompt": "公众号封面，主题：{topic}，学术专业风格，严谨构图，知识感，高质量，无文字，9:16比例",
        "font_recommendation": "宋体",
        "color_recommendation": "#2C3E50",
        "is_active": True,
    },
]


def init_cover_styles():
    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing = db.query(CoverStyle).first()
        if existing:
            print("封面风格数据已存在，跳过初始化")
            return
        
        # 插入默认数据
        for style_data in DEFAULT_COVER_STYLES:
            style = CoverStyle(**style_data)
            db.add(style)
        
        db.commit()
        print(f"已初始化 {len(DEFAULT_COVER_STYLES)} 种封面风格")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_cover_styles()