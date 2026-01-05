from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserRole
from ..schemas import AuthRequest, AuthResponse, UserOut
from ..security import AuthError, create_access_token, verify_telegram_init_data

router = APIRouter(tags=["auth"])


@router.post("/auth/telegram", response_model=AuthResponse)
def auth_telegram(payload: AuthRequest, db: Session = Depends(get_db)):
    try:
        user_data = verify_telegram_init_data(payload.init_data)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid init data")

    tg_id = str(user_data.get("id"))
    username = user_data.get("username")
    full_name = " ".join(filter(None, [user_data.get("first_name"), user_data.get("last_name")])) or None

    user = db.query(User).filter(User.tg_id == tg_id).first()
    if not user:
        user = User(tg_id=tg_id, username=username, full_name=full_name, role=UserRole.student)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.username = username
        user.full_name = full_name
        db.commit()
        db.refresh(user)

    if not user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email_required")

    token = create_access_token(user.id, user.role.value)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))
