from app.database import SessionLocal, engine, Base
from app.models.template_category import TemplateCategory
from app.models.template import Template


def seed():
    print("Seeding template categories...")
    
    Base.metadata.create_all(bind=engine, tables=[TemplateCategory.__table__])
    
    db = SessionLocal()
    
    try:
        existing = db.query(TemplateCategory).count()
        if existing > 0:
            print(f"Found {existing} existing categories, skipping seed")
            return
        
        categories = [
            TemplateCategory(
                name="思维可视化",
                code="thinking",
                description="思维导图、概念图、流程图等思维可视化模板",
                icon="BrainOutlined",
                sort_order=1,
                is_active=True
            ),
            TemplateCategory(
                name="数学可视化",
                code="math",
                description="数学公式、几何图形、函数图像等数学可视化模板",
                icon="CalculatorOutlined",
                sort_order=2,
                is_active=True
            ),
            TemplateCategory(
                name="数据可视化",
                code="data",
                description="图表、数据展示、统计分析等数据可视化模板",
                icon="BarChartOutlined",
                sort_order=3,
                is_active=True
            ),
            TemplateCategory(
                name="动画效果",
                code="animation",
                description="转场动画、特效演示等动画效果模板",
                icon="PlayCircleOutlined",
                sort_order=4,
                is_active=True
            ),
            TemplateCategory(
                name="教育教学",
                code="education",
                description="知识点讲解、课程演示等教育教学模板",
                icon="BookOutlined",
                sort_order=5,
                is_active=True
            ),
        ]
        
        for cat in categories:
            db.add(cat)
        
        db.commit()
        print(f"Added {len(categories)} template categories")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("Seed completed!")


if __name__ == "__main__":
    seed()
