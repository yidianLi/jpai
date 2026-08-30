"""认证接口"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_ai_db
from ..models.dict import AiUser
from ..core.auth import create_access_token, get_current_user, verify_password, get_password_hash
from ..config import settings

router = APIRouter()


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_ai_db)):
    user = db.query(AiUser).filter(AiUser.user_code == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    # 原系统密码是MD5，这里兼容：先比对明文MD5，再比对bcrypt
    import hashlib
    md5_pwd = hashlib.md5(form_data.password.encode()).hexdigest()
    if user.password != md5_pwd and not verify_password(form_data.password, user.password or ""):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.state != 1:
        raise HTTPException(status_code=403, detail="账号已停用")
    token = create_access_token(
        data={"sub": str(user.user_id), "name": user.user_name},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": token, "token_type": "bearer",
        "user": {
            "id": user.user_id, "code": user.user_code, "name": user.user_name,
            "role": user.role_name, "is_admin": user.is_admin,
            "company_id": user.company_id, "dept_id": user.dept_id
        }
    }


@router.get("/me")
def get_me(user: AiUser = Depends(get_current_user)):
    return {
        "id": user.user_id, "code": user.user_code, "name": user.user_name,
        "role": user.role_name, "is_admin": user.is_admin,
        "company_id": user.company_id, "dept_id": user.dept_id,
        "mobile": user.mobile, "email": user.email
    }


@router.post("/change-password")
def change_password(old_pwd: str, new_pwd: str, user: AiUser = Depends(get_current_user), db: Session = Depends(get_ai_db)):
    import hashlib
    md5_old = hashlib.md5(old_pwd.encode()).hexdigest()
    if user.password != md5_old and not verify_password(old_pwd, user.password or ""):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.password = get_password_hash(new_pwd)
    db.commit()
    return {"message": "密码修改成功"}
