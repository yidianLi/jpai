"""认证与权限"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_ai_db
from ..models.dict import AiUser

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")


def verify_password(plain: str, hashed: str) -> bool:
    """兼容原系统MD5和bcrypt两种密码格式"""
    if not hashed:
        return False
    # 原系统密码是32位MD5哈希
    if len(hashed) == 32 and all(c in '0123456789abcdefABCDEF' for c in hashed):
        import hashlib
        return hashlib.md5(plain.encode('utf-8')).hexdigest().upper() == hashed.upper()
    # 新系统用bcrypt
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def needs_password_upgrade(hashed: str) -> bool:
    return bool(hashed and len(hashed) == 32 and all(c in '0123456789abcdefABCDEF' for c in hashed))


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_ai_db)) -> AiUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录已过期，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(AiUser).filter(AiUser.user_id == user_id).first()
    if user is None or user.state != 1 or int(payload.get("token_version", 0)) != int(user.token_version or 1):
        raise credentials_exception
    return user


def require_admin(user: AiUser = Depends(get_current_user)):
    if user.is_admin != 1:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
