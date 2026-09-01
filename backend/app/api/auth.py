"""认证接口"""
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_ai_db
from ..models.dict import AiUser
from ..core.auth import create_access_token, get_current_user, verify_password, get_password_hash, needs_password_upgrade
from ..config import settings
from ..core.audit import record as record_audit
from ..core.auth import require_admin

router = APIRouter()


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), request: Request = None, db: Session = Depends(get_ai_db)):
    user = db.query(AiUser).filter(AiUser.user_code == form_data.username).first()
    if user and user.locked_until and user.locked_until > datetime.now():
        raise HTTPException(status_code=423, detail="account temporarily locked")
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not verify_password(form_data.password, user.password or ""):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= settings.LOGIN_MAX_FAILURES:
            user.locked_until = datetime.now() + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
        record_audit(db, user, "auth.login", user.user_code, result="failure", request=request)
        db.commit()
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if needs_password_upgrade(user.password or ""):
        user.password = get_password_hash(form_data.password)
        db.commit()
    if user.state != 1:
        raise HTTPException(status_code=403, detail="账号已停用")
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    token = create_access_token(
        data={"sub": str(user.user_id), "name": user.user_name, "token_version": user.token_version or 1},
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

@router.post("/rotate-tokens")
def rotate_tokens(db: Session = Depends(get_ai_db), user: AiUser = Depends(require_admin), request: Request = None):
    count = db.query(AiUser).update({AiUser.token_version: AiUser.token_version + 1}, synchronize_session=False)
    record_audit(db, user, "auth.token.rotate", "all-users", after={"affected_users": count}, request=request)
    db.commit()
    return {"message": "all access tokens invalidated", "affected_users": count}


@router.post("/change-password")
def change_password(old_pwd: str, new_pwd: str, user: AiUser = Depends(get_current_user), db: Session = Depends(get_ai_db)):
    if not verify_password(old_pwd, user.password or ""):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.password = get_password_hash(new_pwd)
    db.commit()
    return {"message": "密码修改成功"}
