import json
from app.database import SessionLocal
from app.models.video_topic_category import VideoTopicCategory


DEFAULT_VIDEO_TOPICS = [
    {
        "name": "思维方法论",
        "icon": "🧠",
        "description": "认知提升、思维模型、学习方法",
        "example_topics": ["世界十大顶级思维", "刻意练习法则", "复利思维的力量", "终身学习的方法", "逆向思维技巧"],
        "topic_generation_prompt": "生成思维方法论相关的热门主题，如认知提升、思维模型、学习方法、决策技巧等",
        "system_prompt": """你是一个思维方法论和认知科学的专家。

## 输出格式
【视频内容】

### 第 1 点：[标题，8-10字]
- 内容：[30-40字，阐述核心观点]
- 动态图：[15-20字，简洁描述动态效果]

...（以此类推）

## 重要规则
1. 内容简洁精炼，严格控制在规定字数内
2. 动态图描述要简短具体，易于可视化
3. 每个要点独立且有深度
4. 直接输出结果，不要输出思考过程""",
        "sort_order": 1
    },
    {
        "name": "情绪治愈",
        "icon": "💖",
        "description": "心理调节、情绪疏导、自我疗愈",
        "example_topics": ["治愈焦虑的5个方法", "情绪管理技巧", "如何走出低谷期", "自我疗愈的力量", "接纳不完美的自己"],
        "topic_generation_prompt": "生成情绪治愈相关的热门主题，如心理调节、情绪疏导、自我疗愈、心理健康等",
        "system_prompt": """你是一个心理咨询和情绪管理的专家。

## 输出格式
【视频内容】

### 第 1 点：[标题，8-10字]
- 内容：[30-40字，温暖治愈的内容]
- 动态图：[15-20字，柔和舒缓的动态效果]

...（以此类推）

## 重要规则
1. 语言温暖治愈，有同理心
2. 动态图描述要柔和舒缓
3. 内容要有实用性和情感共鸣
4. 直接输出结果，不要询问用户""",
        "sort_order": 2
    },
    {
        "name": "数学公式",
        "icon": "📐",
        "description": "经典公式、定理证明、几何原理",
        "example_topics": ["傅里叶变换可视化", "欧拉公式之美", "勾股定理证明", "微积分的本质", "概率论基础"],
        "topic_generation_prompt": "生成数学公式可视化相关的热门主题，如经典公式、定理证明、几何原理、数学概念等",
        "system_prompt": """你是一个数学和科学可视化的专家。

## 输出格式
【核心概念】
[30-40字，简述核心数学概念]

【关键公式】
- [公式1]：[10-20字说明]
- [公式2]：[10-20字说明]

【动态演示】
[20-30字，描述可视化动画过程]

【视觉亮点】
[15-20字，强调视觉效果]

## 重要规则
1. 公式要准确且简洁
2. 动态演示要具体可实现
3. 视觉效果要有冲击力
4. 直接输出结果，不要解释""",
        "sort_order": 3
    },
    {
        "name": "健康习惯",
        "icon": "🏃",
        "description": "生活习惯、运动健身、养生方法",
        "example_topics": ["早起习惯养成", "运动健身技巧", "健康饮食原则", "改善睡眠质量", "科学喝水方法"],
        "topic_generation_prompt": "生成健康习惯相关的热门主题，如生活习惯、运动健身、养生方法、健康饮食等",
        "system_prompt": """你是一个健康生活方式和习惯养成的专家。

## 输出格式
【视频内容】

### 第 1 点：[标题，8-10字]
- 内容：[30-40字，实用的健康建议]
- 动态图：[15-20字，生动的动态展示]

...（以此类推）

## 重要规则
1. 内容要科学实用
2. 动态图要生动易理解
3. 强调可操作性和效果
4. 直接输出结果，不要输出思考过程""",
        "sort_order": 4
    },
    {
        "name": "财富认知",
        "icon": "💰",
        "description": "投资理财、财富思维、经济学原理",
        "example_topics": ["穷人思维vs富人思维", "复利的力量", "投资基础知识", "财富自由之路", "经济学原理"],
        "topic_generation_prompt": "生成财富认知相关的热门主题，如投资理财、财富思维、经济学原理、财务管理等",
        "system_prompt": """你是一个财富认知和经济学的专家。

## 输出格式
【视频内容】

### 第 1 点：[标题，8-10字]
- 内容：[30-40字，深刻的财富观点]
- 动态图：[15-20字，形象的动态展示]

...（以此类推）

## 重要规则
1. 内容要有启发性
2. 动态图要形象易懂
3. 强调思维转变和行动
4. 直接输出结果，不要询问用户""",
        "sort_order": 5
    },
    {
        "name": "职场技能",
        "icon": "💼",
        "description": "工作效率、职场沟通、职业发展",
        "example_topics": ["时间管理方法", "沟通技巧提升", "职场晋升策略", "高效工作法则", "领导力培养"],
        "topic_generation_prompt": "生成职场技能相关的热门主题，如工作效率、职场沟通、职业发展、领导力等",
        "system_prompt": """你是一个职场发展和职业技能的专家。

## 输出格式
【视频内容】

### 第 1 点：[标题，8-10字]
- 内容：[30-40字，实用的职场建议]
- 动态图：[15-20字，清晰的动态展示]

...（以此类推）

## 重要规则
1. 内容要实战可操作
2. 动态图要清晰易懂
3. 强调职场实用性
4. 直接输出结果，不要输出思考过程""",
        "sort_order": 6
    }
]


def init_video_topics():
    """初始化视频主题方向"""
    db = SessionLocal()
    
    try:
        for topic_data in DEFAULT_VIDEO_TOPICS:
            existing = db.query(VideoTopicCategory).filter(
                VideoTopicCategory.name == topic_data["name"]
            ).first()
            
            if existing:
                print(f"Category '{topic_data['name']}' already exists, updating...")
                existing.icon = topic_data["icon"]
                existing.description = topic_data["description"]
                existing.example_topics = json.dumps(topic_data["example_topics"], ensure_ascii=False)
                existing.topic_generation_prompt = topic_data["topic_generation_prompt"]
                existing.system_prompt = topic_data["system_prompt"]
                existing.sort_order = topic_data["sort_order"]
            else:
                print(f"Creating category '{topic_data['name']}'...")
                category = VideoTopicCategory(
                    name=topic_data["name"],
                    icon=topic_data["icon"],
                    description=topic_data["description"],
                    example_topics=json.dumps(topic_data["example_topics"], ensure_ascii=False),
                    topic_generation_prompt=topic_data["topic_generation_prompt"],
                    system_prompt=topic_data["system_prompt"],
                    is_active=True,
                    sort_order=topic_data["sort_order"]
                )
                db.add(category)
        
        db.commit()
        print("\nVideo topic categories initialized successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_video_topics()