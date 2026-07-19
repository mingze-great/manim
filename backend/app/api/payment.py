from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import time

from app.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.subscription import Order, Subscription, SUBSCRIPTION_PLANS
from app.api.auth import get_current_user
from app.services.wechat_pay import get_wechat_pay_service

router = APIRouter(prefix="/payment", tags=["payment"])


class CreateOrderRequest(BaseModel):
    plan: str


class OrderResponse(BaseModel):
    order_id: str
    plan: str
    amount: int
    status: str
    code_url: str | None = None


class SubscriptionResponse(BaseModel):
    plan: str
    daily_quota: int
    max_projects: int
    expires_at: str | None
    features: List[str]


def generate_order_id() -> str:
    """生成订单号"""
    return f"WX{int(time.time() * 1000)}"


@router.post("/create", response_model=OrderResponse)
async def create_payment_order(
    request: CreateOrderRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """创建微信支付订单"""
    plan = request.plan
    
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="无效的套餐")
    
    plan_config = SUBSCRIPTION_PLANS[plan]
    if plan_config["price"] == 0:
        raise HTTPException(status_code=400, detail="免费套餐不需要支付")
    
    order_id = generate_order_id()
    amount = plan_config["price"]
    
    order = Order(
        user_id=current_user.id,
        order_id=order_id,
        plan=plan,
        amount=amount,
        status="pending",
        description=f"Manim视频平台-{plan_config['name']}"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    wx_service = get_wechat_pay_service()
    result = wx_service.create_unified_order(
        order_id=order_id,
        amount=amount,
        description=order.description
    )
    
    if not result["success"]:
        order.status = "cancelled"
        db.commit()
        raise HTTPException(status_code=500, detail=f"创建支付订单失败: {result['error']}")
    
    return OrderResponse(
        order_id=order_id,
        plan=plan,
        amount=amount,
        status="pending",
        code_url=result.get("code_url")
    )


@router.post("/wx/notify")
async def wechat_pay_notify(
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)]
):
    """微信支付回调"""
    from fastapi import Request
    
    async def process_notify(request: Request):
        xml_data = await request.body()
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_data.decode('utf-8'))
        params = {child.tag: child.text for child in root}
        
        if params.get('return_code') != 'SUCCESS':
            return "<xml><return_code><![CDATA[FAIL]]></return_code></xml>"
        
        order_id = params.get('out_trade_no')
        transaction_id = params.get('transaction_id')
        
        wx_service = get_wechat_pay_service()
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order or order.status == "paid":
            return "<xml><return_code><![CDATA[SUCCESS]]></return_code></xml>"
        
        if not wx_service.verify_notify(params):
            return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[签名验证失败]]></return_msg></xml>"
        
        order.status = "paid"
        order.transaction_id = transaction_id
        order.paid_at = datetime.utcnow()
        db.commit()
        
        update_user_subscription(order.user_id, order.plan, db)
        
        return "<xml><return_code><![CDATA[SUCCESS]]></return_code></xml>"
    
    return await process_notify(background_tasks)


def update_user_subscription(user_id: int, plan: str, db: Session):
    """更新用户订阅"""
    plan_config = SUBSCRIPTION_PLANS.get(plan)
    if not plan_config:
        return
    
    expires_days = 30
    
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    
    if subscription:
        subscription.plan = plan
        subscription.daily_quota = plan_config["daily_quota"]
        subscription.max_projects = plan_config["max_projects"]
        if plan == "free":
            subscription.expires_at = None
        else:
            if subscription.expires_at and subscription.expires_at > datetime.utcnow():
                subscription.expires_at += timedelta(days=expires_days)
            else:
                subscription.expires_at = datetime.utcnow() + timedelta(days=expires_days)
    else:
        subscription = Subscription(
            user_id=user_id,
            plan=plan,
            daily_quota=plan_config["daily_quota"],
            max_projects=plan_config["max_projects"],
            expires_at=datetime.utcnow() + timedelta(days=expires_days) if plan != "free" else None
        )
        db.add(subscription)
    
    db.commit()


@router.get("/plans")
async def get_subscription_plans():
    """获取所有订阅套餐"""
    return SUBSCRIPTION_PLANS


@router.get("/my-subscription", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取当前用户订阅信息"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        return SubscriptionResponse(
            plan="free",
            daily_quota=100,
            max_projects=10,
            expires_at=None,
            features=SUBSCRIPTION_PLANS["free"]["features"]
        )
    
    plan_config = SUBSCRIPTION_PLANS.get(subscription.plan, SUBSCRIPTION_PLANS["free"])
    
    return SubscriptionResponse(
        plan=subscription.plan,
        daily_quota=subscription.daily_quota,
        max_projects=subscription.max_projects,
        expires_at=subscription.expires_at.isoformat() if subscription.expires_at else None,
        features=plan_config["features"]
    )


@router.get("/orders")
async def get_my_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取当前用户的订单列表"""
    orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(Order.created_at.desc()).limit(20).all()
    
    return [
        {
            "order_id": o.order_id,
            "plan": o.plan,
            "amount": o.amount,
            "status": o.status,
            "created_at": o.created_at.isoformat(),
            "paid_at": o.paid_at.isoformat() if o.paid_at else None,
        }
        for o in orders
    ]


@router.post("/query/{order_id}")
async def query_order_status(
    order_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """查询订单状态"""
    order = db.query(Order).filter(
        Order.order_id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if order.status == "paid":
        return {"status": "paid", "message": "支付成功"}
    
    wx_service = get_wechat_pay_service()
    result = wx_service.query_order(order_id)
    
    if result["success"]:
        trade_state = result.get("trade_state")
        if trade_state == "SUCCESS":
            order.status = "paid"
            order.paid_at = datetime.utcnow()
            db.commit()
            update_user_subscription(order.user_id, order.plan, db)
            return {"status": "paid", "message": "支付成功"}
        elif trade_state == "NOTPAY":
            return {"status": "pending", "message": "等待支付"}
        elif trade_state == "CLOSED":
            order.status = "cancelled"
            db.commit()
            return {"status": "cancelled", "message": "订单已关闭"}
        else:
            return {"status": "pending", "message": result.get("trade_state_desc", "处理中")}
    
    return {"status": "pending", "message": "查询中"}


class UsageStatsResponse(BaseModel):
    daily_quota: int
    used_today: int
    weekly_usage: int
    total_usage: int


@router.get("/usage-stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """获取用户使用统计"""
    from app.models.subscription import Subscription
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    
    daily_quota = 100
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    if subscription:
        daily_quota = subscription.daily_quota
    
    used_today = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status == ProjectStatus.COMPLETED.value,
        Project.updated_at >= today_start
    ).count()
    
    weekly_usage = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status == ProjectStatus.COMPLETED.value,
        Project.updated_at >= week_start
    ).count()
    
    total_usage = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status == ProjectStatus.COMPLETED.value
    ).count()
    
    return UsageStatsResponse(
        daily_quota=daily_quota,
        used_today=used_today,
        weekly_usage=weekly_usage,
        total_usage=total_usage
    )
