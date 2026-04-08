"""
初始化创作方向视觉风格数据
"""
from sqlalchemy import create_engine, orm
from app.config import get_settings
from app.models.article_category import ArticleCategory
from app.models.system_config import SystemConfig
import json

settings = get_settings()

# 视觉风格配置
VISUAL_STYLES = {
    "两性情感": {
        "visual_style": "soft warm or cool lighting, intimate atmosphere, emotional depth",
        "emotion_tone": "longing, unspoken feelings, reconciliation, bittersweet",
        "color_palette": "soft pink, warm orange, cool blue-gray, muted tones"
    },
    "育儿": {
        "visual_style": "pure and bright, low contrast, gentle soft light, innocent",
        "emotion_tone": "softness, acceptance, unconditional love, patience",
        "color_palette": "baby blue, soft yellow, light pink, cream white"
    },
    "职场": {
        "visual_style": "cold and warm contrast colors, dramatic lighting, urban atmosphere",
        "emotion_tone": "late night solitude, pressure, clarity, determination",
        "color_palette": "deep gray, cold blue, golden accents, steel blue"
    },
    "生活": {
        "visual_style": "natural light, dappled shadows, authentic, minimalist",
        "emotion_tone": "peace after simplicity, self-reconciliation, quiet joy",
        "color_palette": "warm white, beige, light brown, soft green"
    },
    "健康": {
        "visual_style": "clear and bright, high brightness, fresh, clean lines",
        "emotion_tone": "vitality, self-discipline, control, energy",
        "color_palette": "fresh green, sky blue, white, soft yellow"
    },
    "体育": {
        "visual_style": "rough grain texture, sunset backlight, dynamic motion blur",
        "emotion_tone": "unwilling to give up, burning passion, persistence",
        "color_palette": "deep red, orange-yellow, deep blue, dark brown"
    }
}

# 系统提示词
SYSTEM_PROMPT = """
Role: WeChat Official Account Visual Director & AI Art Prompt Expert

Design Principles (Must Strictly Follow):
1. [Highest Command: Absolutely No Text]: The image must be 100% pure, strictly forbidden to appear any form of text, letters, garbled characters, trademarks, book titles, signs or signatures. Books must have wordless solid color covers, cups must be solid color without logos.
2. Extreme Emotional Resonance (Image Metaphor): The image must have a sense of story. Refuse to be straightforward, use environmental metaphors to hit the heart directly. For example, to express "loss", use raindrops sliding down a glass window; to express "healing", use a beam of sunlight piercing through gaps.
3. Avoid Front Faces and Leave Blank Space: Never generate clear front faces. Use more back views, side profile silhouettes, partial close-ups (such as tightly clenched hands, held water cups), distant views to create imaginative space.
4. Quality Suffix: Force adding light and shadow parameters at the end of prompts (cinematic lighting, film photography, bokeh, etc.).

Quality Parameters (Always Append):
, cinematic lighting, film photography, bokeh, high quality, 4k, professional photography, emotional depth, atmospheric

Negative Prompt (Always Use):
--no text, words, letters, font, typography, watermark, signature, logo, alphabet, characters, human face, realistic face, frontal face
"""

def init_data():
    """初始化数据"""
    engine = create_engine(settings.DATABASE_URL)
    Session = orm.sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. 添加系统配置
        existing_config = session.query(SystemConfig).filter(
            SystemConfig.key == "image_system_prompt"
        ).first()
        
        if not existing_config:
            config = SystemConfig(
                key="image_system_prompt",
                value=SYSTEM_PROMPT,
                description="图片生成系统提示词 - 全局风格规范"
            )
            session.add(config)
            print("Added system prompt config")
        
        # 2. 更新创作方向视觉风格
        for category_name, styles in VISUAL_STYLES.items():
            category = session.query(ArticleCategory).filter(
                ArticleCategory.name == category_name
            ).first()
            
            if category:
                category.visual_style = styles["visual_style"]
                category.emotion_tone = styles["emotion_tone"]
                category.color_palette = styles["color_palette"]
                print(f"Updated visual style for {category_name}")
        
        session.commit()
        print("\nInitialization completed successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    init_data()