"""
更新模板 prompt 的迁移脚本
运行方式: python backend/scripts/update_template_prompts.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal
from app.utils.init_templates import DEFAULT_TEMPLATE_PROMPT, update_existing_template_prompts


def main():
    print("=" * 50)
    print("更新模板 Prompt 脚本")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        updated = update_existing_template_prompts(db)
        print(f"\n完成！共更新 {updated} 个模板")
        
        from app.models.template import Template
        templates = db.query(Template).filter(Template.is_system == True).all()
        print(f"\n当前系统模板列表：")
        for t in templates:
            prompt_status = "✅ 有 prompt" if t.prompt else "❌ 无 prompt"
            print(f"  - [{t.id}] {t.name}: {prompt_status}")
            
    except Exception as e:
        print(f"错误: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()