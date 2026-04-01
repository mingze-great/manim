import os

CODE_CACHE_DIR = "/tmp/manim_code_cache"


class CodeCache:
    @staticmethod
    def save(project_id: int, code: str):
        os.makedirs(CODE_CACHE_DIR, exist_ok=True)
        cache_file = f"{CODE_CACHE_DIR}/code_{project_id}.py"
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(code)
    
    @staticmethod
    def load(project_id: int) -> str | None:
        cache_file = f"{CODE_CACHE_DIR}/code_{project_id}.py"
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    @staticmethod
    def delete(project_id: int):
        cache_file = f"{CODE_CACHE_DIR}/code_{project_id}.py"
        if os.path.exists(cache_file):
            os.remove(cache_file)