import asyncio
from openai import AsyncOpenAI

async def test():
    client = AsyncOpenAI(
        api_key="sk-cb3cf0d966b84924827b1000d33ee1f5",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    messages = [{"role": "user", "content": "你是谁"}]
    
    print("开始测试阿里云百炼 API...")
    print("=" * 50)
    
    try:
        response = await client.chat.completions.create(
            model="siliconflow/deepseek-v3.2",
            messages=messages,
            extra_body={"enable_thinking": True},
            stream=True,
            stream_options={"include_usage": True},
        )
        
        print("\n[思考过程]")
        print("-" * 50)
        
        async for chunk in response:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    print(delta.reasoning_content, end="", flush=True)
                if hasattr(delta, "content") and delta.content:
                    print("\n\n[回复内容]")
                    print("-" * 50)
                    print(delta.content, end="", flush=True)
            elif hasattr(chunk, "usage") and chunk.usage:
                print("\n\n[Token 消耗]")
                print("-" * 50)
                print(chunk.usage)
        
        print("\n\n" + "=" * 50)
        print("测试成功！")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())