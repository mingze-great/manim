from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Order(Base):
    """订单表"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    order_id = Column(String(64), unique=True, index=True, nullable=False)
    transaction_id = Column(String(64), nullable=True)
    
    plan = Column(String(32), nullable=False)  # free, basic, pro, enterprise
    amount = Column(Integer, nullable=False)  # 金额，单位：分
    
    status = Column(String(32), default="pending")  # pending, paid, cancelled, refunded
    
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="orders")


class Subscription(Base):
    """用户订阅表"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    plan = Column(String(32), default="free")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    daily_quota = Column(Integer, default=100)  # 每日额度
    max_projects = Column(Integer, default=10)   # 最大项目数
    
    is_active = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="subscription")


# 订阅套餐配置
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "免费版",
        "price": 0,
        "daily_quota": 100,
        "max_projects": 10,
        "features": ["每日100次额度", "基础模板", "标清导出"],
    },
    "basic": {
        "name": "基础版",
        "price": 9900,  # 99元
        "daily_quota": 500,
        "max_projects": 50,
        "features": ["每日500次额度", "全部模板", "高清导出", "优先渲染"],
    },
    "pro": {
        "name": "专业版",
        "price": 19900,  # 199元
        "daily_quota": 2000,
        "max_projects": 200,
        "features": ["每日2000次额度", "高级模板", "高清导出", "优先渲染", "技术支持"],
    },
    "enterprise": {
        "name": "企业版",
        "price": 49900,  # 499元
        "daily_quota": 10000,
        "max_projects": -1,  # 无限
        "features": ["无限额度", "私有模板", "4K导出", "专属客服", "API接口", "定制服务"],
    },
}
