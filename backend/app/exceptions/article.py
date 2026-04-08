class ArticleGenerationError(Exception):
    """文章生成错误基类"""
    pass


class LLMError(ArticleGenerationError):
    """LLM调用错误"""
    pass


class ValidationError(ArticleGenerationError):
    """参数验证错误"""
    pass


class RateLimitError(ArticleGenerationError):
    """频率限制错误"""
    pass


class ContentFilterError(ArticleGenerationError):
    """内容过滤错误"""
    pass