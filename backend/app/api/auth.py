from datetime import datetime, timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from collections import defaultdict
import time
import secrets

from app.database import get_db
from app.config import get_settings
from app.models.user import User, AuditLog
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

token_blacklist = set()
rate_limit_store = defaultdict(list)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def generate_random_username(db: Session) -> str:
    while True:
        candidate = f"创作者{secrets.token_hex(3)}"
        exists = db.query(User).filter(User.username == candidate).first()
        if not exists:
            return candidate


def build_placeholder_email(username: str, phone: str | None) -> str:
    suffix = phone or secrets.token_hex(4)
    return f"{username}_{suffix}@placeholder.local"


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def check_rate_limit(identifier: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
    now = time.time()
    window_start = now - window_seconds
    
    rate_limit_store[identifier] = [
        t for t in rate_limit_store[identifier] if t > window_start
    ]
    
    if len(rate_limit_store[identifier]) >= max_requests:
        return False
    
    rate_limit_store[identifier].append(now)
    return True


def log_audit(db: Session, user_id: Optional[int], username: Optional[str], 
              action: str, resource: Optional[str] = None, resource_id: Optional[int] = None,
              details: Optional[str] = None, request: Optional[Request] = None):
    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent")[:500] if request and request.headers.get("user-agent") else None
    
    audit_log = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit_log)
    db.commit()


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None, "用户不存在"
    if not verify_password(password, user.hashed_password):
        return None, "密码错误"
    if not user.is_active:
        return None, "账号已被禁用"
    if not user.is_approved and not user.is_admin:
        return None, "账号正在等待审核，请联系管理员"
    if user.is_expired():
        return None, "账号已过期，请联系续费"
    return user, None


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
):
    if token in token_blacklist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号已被禁用，请联系管理员",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_approved and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号正在等待审核",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号已过期，请联系续费",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


@router.post("/register", response_model=UserResponse)
def register(
    user_data: dict,
    db: Annotated[Session, Depends(get_db)],
    request: Request
):
    username = (user_data.get("username") or "").strip()
    phone = (user_data.get("phone") or "").strip()
    password = user_data.get("password")
    email = (user_data.get("email") or "").strip()

    if not username:
        username = generate_random_username(db)
    
    if not all([username, phone, password]):
        raise HTTPException(status_code=400, detail="缺少必填信息：用户名、手机号、密码")

    if not phone.isdigit() or len(phone) != 11 or not phone.startswith('1'):
        raise HTTPException(status_code=400, detail="请输入有效的11位手机号")
    
    if not check_rate_limit(f"register:{request.client.host}", max_requests=5, window_seconds=3600):
        raise HTTPException(status_code=429, detail="注册过于频繁，请稍后再试")
    
    # 检查用户名和手机号
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    db_user = db.query(User).filter(User.phone == phone).first()
    if db_user:
        raise HTTPException(status_code=400, detail="手机号已被注册")

    if not email:
        email = build_placeholder_email(username, phone)
    else:
        db_user = db.query(User).filter(User.email == email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        phone=phone,
        hashed_password=hashed_password,
        is_approved=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_audit(db, new_user.id, new_user.username, "USER_REGISTER", 
              details=f"新用户注册，等待管理员审批", request=request)
    
    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
    request: Request
):
    if not check_rate_limit(f"login:{form_data.username}", max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="登录尝试过于频繁，请稍后再试")
    
    user, error = authenticate_user(db, form_data.username, form_data.password)
    if error:
        log_audit(db, None, form_data.username, "LOGIN_FAILED", details=error, request=request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    log_audit(db, user.id, user.username, "LOGIN_SUCCESS", details="用户登录", request=request)
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/change-password")
def change_password(
    payload: dict,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    request: Request,
):
    current_password = payload.get("current_password")
    new_password = payload.get("new_password")

    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="请填写当前密码和新密码")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="新密码至少8位")
    if not any(ch.isalpha() for ch in new_password) or not any(ch.isdigit() for ch in new_password):
        raise HTTPException(status_code=400, detail="新密码必须包含字母和数字")

    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="当前密码错误")

    current_user.hashed_password = get_password_hash(new_password)
    db.commit()

    log_audit(db, current_user.id, current_user.username, "PASSWORD_CHANGE", details="用户修改密码", request=request)
    return {"message": "密码修改成功"}


@router.post("/logout")
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    request: Request
):
    token_blacklist.add(token)
    log_audit(db, current_user.id, current_user.username, "LOGOUT", details="用户登出", request=request)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
