"""
提示词构建服务 - 根据文章方向和内容生成符合微信审美的图片提示词
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.article_category import ArticleCategory


class PromptBuilderService:
    """提示词构建器"""
    
    # 情绪-场景映射库
    EMOTION_SCENE_MAP = {
        "失落": "raindrops sliding down a glass window, blurred city lights outside, melancholic atmosphere",
        "治愈": "a beam of sunlight piercing through gaps, warm golden light, peaceful moment",
        "孤独": "a single figure standing at the window at night, city lights in distance, solitude",
        "温暖": "two cups of coffee on a wooden table, soft morning light, intimate moment",
        "希望": "a small sprout breaking through concrete, morning dew, new beginning",
        "焦虑": "scattered papers on a desk late at night, single lamp light, restless mind",
        "释怀": "an open window with white curtains flowing in the wind, sense of release",
        "陪伴": "two silhouettes sitting side by side watching sunset, togetherness",
        "成长": "footprints on a mountain trail, morning mist, personal journey",
        "坚强": "a lone tree standing in a storm, resilience, unbroken spirit",
        "幸福": "sunlight filtering through leaves, warm embrace, joyful serenity",
        "期待": "an open door with light streaming through, anticipation, new chapter"
    }
    
    # 默认创作方向视觉风格
    DEFAULT_VISUAL_STYLES = {
        "两性情感": {
            "visual_style": "soft warm or cool lighting, intimate atmosphere",
            "emotion_tone": "longing, unspoken feelings, reconciliation",
            "color_palette": "soft pink, warm orange, cool blue-gray"
        },
        "育儿": {
            "visual_style": "pure and bright, low contrast, gentle light",
            "emotion_tone": "softness, acceptance, unconditional love",
            "color_palette": "baby blue, soft yellow, light pink"
        },
        "职场": {
            "visual_style": "cold and warm contrast colors, dramatic lighting",
            "emotion_tone": "late night solitude, pressure, clarity",
            "color_palette": "deep gray, cold blue, golden accents"
        },
        "生活": {
            "visual_style": "natural light, dappled shadows, authentic",
            "emotion_tone": "peace after simplicity, self-reconciliation",
            "color_palette": "warm white, beige, light brown"
        },
        "健康": {
            "visual_style": "clear and bright, high brightness, fresh",
            "emotion_tone": "vitality, self-discipline, control",
            "color_palette": "fresh green, sky blue, white"
        },
        "体育": {
            "visual_style": "rough grain texture, sunset backlight, dynamic",
            "emotion_tone": "unwilling to give up, burning passion",
            "color_palette": "deep red, orange-yellow, deep blue"
        }
    }
    
    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT = """
Role: WeChat Official Account Visual Director & AI Art Prompt Expert

Design Principles (Must Strictly Follow):
1. [Highest Command: Absolutely No Text]: The image must be 100% pure, strictly forbidden to appear any form of text, letters, garbled characters, trademarks, book titles, signs or signatures. Books must have wordless solid color covers, cups must be solid color without logos.
2. Extreme Emotional Resonance (Image Metaphor): The image must have a sense of story. Refuse to be straightforward, use environmental metaphors to hit the heart directly.
3. Avoid Front Faces and Leave Blank Space: Never generate clear front faces. Use more back views, side profile silhouettes, partial close-ups (such as tightly clenched hands, held water cups), distant views to create imaginative space.
4. Quality Suffix: Force adding light and shadow parameters at the end of prompts (cinematic lighting, film photography, bokeh, etc.).

Quality Parameters (Always Append):
, cinematic lighting, film photography, bokeh, high quality, 4k, professional photography, emotional depth

Negative Prompt (Always Use):
--no text, words, letters, font, typography, watermark, signature, logo, alphabet, characters, human face, realistic face, frontal face
"""

    def __init__(self, db: Session):
        self.db = db
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self.DEFAULT_SYSTEM_PROMPT
    
    def get_category_style(self, category: str) -> dict:
        """获取创作方向的视觉风格"""
        db_category = self.db.query(ArticleCategory).filter(
            ArticleCategory.name == category
        ).first()
        
        if db_category:
            return {
                "visual_style": db_category.visual_style or "",
                "emotion_tone": db_category.emotion_tone or "",
                "color_palette": db_category.color_palette or "",
                "image_prompt_template": db_category.image_prompt_template or ""
            }
        
        # 返回默认风格
        return self.DEFAULT_VISUAL_STYLES.get(category, {
            "visual_style": "natural lighting, authentic atmosphere",
            "emotion_tone": "peaceful, contemplative",
            "color_palette": "neutral tones"
        })
    
    def detect_emotion(self, text: str) -> str:
        """
        分析文案情绪
        
        参数:
            text: 文案文本
        
        返回:
            情绪关键词
        """
        # 情绪词汇库
        emotion_keywords = {
            "失落": ["失落", "难过", "伤心", "痛苦", "悲伤", "绝望"],
            "治愈": ["治愈", "温暖", "幸福", "美好", "感动", "安慰"],
            "孤独": ["孤独", "寂寞", "一个人", "独自", "孤单"],
            "温暖": ["温暖", "陪伴", "在一起", "相爱", "关心"],
            "希望": ["希望", "期待", "未来", "梦想", "相信"],
            "焦虑": ["焦虑", "压力", "担心", "害怕", "紧张"],
            "释怀": ["释怀", "放下", "原谅", "理解", "接受"],
            "成长": ["成长", "改变", "进步", "努力", "坚强"]
        }
        
        # 统计每种情绪出现次数
        emotion_scores = {}
        for emotion, keywords in emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                emotion_scores[emotion] = score
        
        # 返回得分最高的情绪
        if emotion_scores:
            return max(emotion_scores, key=emotion_scores.get)
        
        return "温暖"  # 默认情绪
    
    def generate_scene_description(self, context: str, emotion: str = None) -> str:
        """
        根据文案内容生成场景描述
        
        参数:
            context: 文案片段
            emotion: 指定情绪（可选）
        
        返回:
            场景描述（英文）
        """
        # 如果未指定情绪，自动检测
        if not emotion:
            emotion = self.detect_emotion(context)
        
        # 返回对应场景
        return self.EMOTION_SCENE_MAP.get(emotion, self.EMOTION_SCENE_MAP["温暖"])
    
    def build_prompt(
        self,
        topic: str,
        category: str,
        context: str = "",
        image_type: str = "content"
    ) -> str:
        """
        构建完整的图片提示词
        
        参数:
            topic: 文章主题
            category: 创作方向
            context: 插入位置前的文案片段（用于提取场景）
            image_type: cover 或 content
        
        返回:
            完整的英文提示词
        """
        # 1. 获取系统提示词
        system_prompt = self.get_system_prompt()
        
        # 2. 获取方向风格
        style = self.get_category_style(category)
        
        # 3. 提取场景描述
        scene = self.generate_scene_description(context)
        
        # 4. 构建提示词
        if image_type == "cover":
            prompt = f"""
{system_prompt}

Category: {category}
Visual Style: {style['visual_style']}
Emotion Tone: {style['emotion_tone']}
Color Palette: {style['color_palette']}

Cover Image Concept:
- Topic: {topic}
- Scene: {scene}
- Composition: Clean minimalist design, strong emotional resonance, no text or lettering
- Aspect: Cinematic horizontal format

Quality: cinematic lighting, film photography, bokeh, high quality, 4k, professional photography, emotional depth
            """.strip()
        else:
            # 内容图
            prompt = f"""
{system_prompt}

Category: {category}
Visual Style: {style['visual_style']}
Emotion Tone: {style['emotion_tone']}
Color Palette: {style['color_palette']}

Content Image Concept:
- Topic: {topic}
- Context: {context[:100] if context else topic}
- Scene: {scene}
- Composition: Atmospheric mood shot, emotional depth, no faces or text
- Aspect: Vertical or square format

Quality: cinematic lighting, film photography, bokeh, high quality, 4k, professional photography, emotional depth
            """.strip()
        
        return prompt
