from app.utils.llm_factory import LLMFactory


class ScriptFormatter:
    """文案格式转换服务 - 将用户输入转换为标准格式"""
    
    @staticmethod
    async def format_user_script(user_script: str) -> str:
        """
        将用户输入的文案转换为标准视频内容格式
        保留用户的所有原始内容，只调整格式
        """
        client = LLMFactory.get_client()
        
        prompt = f"""请将以下用户文案转换为标准的视频内容格式。

## 用户文案
{user_script}

## 转换规则
1. **保留所有内容**：不删除、不修改用户的任何观点和信息
2. **标准格式**：
```
【视频内容】

### 第 1 点：[提取或生成标题，8-10字]
- 内容：[用户原文，30-40字]
- 动态图：[基于内容生成简短描述，15-20字]

### 第 2 点：[标题]
- 内容：[用户原文]
- 动态图：[描述]

...（以此类推）
```

3. **内容分段**：
   - 如果用户文案已有分段，按段落划分
   - 如果没有分段，按逻辑含义划分为3-8个要点
   - 每个要点的"内容"必须是用户的原文或核心观点

4. **动态图描述**：
   - 根据内容自动生成
   - 简洁具体，易于可视化

5. **输出格式**：
   - 直接输出转换后的内容
   - 不要输出任何解释或说明

请开始转换："""

        response = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=LLMFactory.get_chat_model(),
            temperature=0.3
        )
        
        return response.strip()
    
    @staticmethod
    def is_formatted_script(text: str) -> bool:
        """检查文案是否已经是标准格式"""
        return "【视频内容】" in text or "### 第" in text