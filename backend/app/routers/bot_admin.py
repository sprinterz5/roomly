import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..config import BOT_ADMIN_TOKEN
from ..database import get_db
from ..models import Club, ClubMember, ClubMemberRole, User, UserRole
from ..schemas import BotClubCreate, BotClubLeaderAssign, BotEmailAssign, BotRoleAssign, BotUserUpsert

router = APIRouter(tags=["bot"])


def require_bot_token(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    if not BOT_ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BOT_ADMIN_TOKEN is not configured",
        )
    if not x_admin_token or not hmac.compare_digest(x_admin_token, BOT_ADMIN_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")


def resolve_user(payload: BotRoleAssign | BotClubLeaderAssign | BotEmailAssign, db: Session) -> User:
    user = None
    if getattr(payload, "user_id", None):
        user = db.get(User, payload.user_id)
    elif getattr(payload, "email", None):
        user = db.query(User).filter(User.email == payload.email).first()
    elif getattr(payload, "tg_id", None):
        user = db.query(User).filter(User.tg_id == payload.tg_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    return user


@router.post("/bot/assign-role")
def bot_assign_role(
    payload: BotRoleAssign,
    _: None = Depends(require_bot_token),
    db: Session = Depends(get_db),
):
    if not payload.user_id and not payload.tg_id and not payload.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id, tg_id, or email required",
        )

    try:
        role = UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid role")

    user = resolve_user(payload, db)
    user.role = role
    db.commit()
    return {"id": user.id, "role": user.role.value}


@router.post("/bot/assign-club-leader")
def bot_assign_club_leader(
    payload: BotClubLeaderAssign,
    _: None = Depends(require_bot_token),
    db: Session = Depends(get_db),
):
    if not payload.user_id and not payload.tg_id and not payload.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id, tg_id, or email required",
        )

    club = None
    if payload.club_id:
        club = db.get(Club, payload.club_id)
    elif payload.club_name:
        club_name = payload.club_name.strip()
        club = db.query(Club).filter(Club.name.ilike(club_name)).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="club_id or club_name required",
        )

    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="club not found")

    user = resolve_user(payload, db)

    membership = (
        db.query(ClubMember)
        .filter(ClubMember.club_id == club.id, ClubMember.user_id == user.id)
        .first()
    )
    if not membership:
        membership = ClubMember(
            club_id=club.id, user_id=user.id, role=ClubMemberRole.leader
        )
        db.add(membership)
    else:
        membership.role = ClubMemberRole.leader

    if user.role != UserRole.admin:
        user.role = UserRole.club_leader

    db.commit()
    return {"club_id": club.id, "user_id": user.id, "role": membership.role.value}


@router.post("/bot/create-club")
def bot_create_club(
    payload: BotClubCreate,
    _: None = Depends(require_bot_token),
    db: Session = Depends(get_db),
):
    club = Club(name=payload.name, owner_user_id=payload.owner_user_id)
    db.add(club)
    db.commit()
    db.refresh(club)
    return {"id": club.id, "name": club.name}


@router.post("/bot/upsert-user")
def bot_upsert_user(
    payload: BotUserUpsert,
    _: None = Depends(require_bot_token),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.tg_id == payload.tg_id).first()
    if not user:
        user = User(
            tg_id=payload.tg_id,
            username=payload.username,
            full_name=payload.full_name,
            role=UserRole.student,
        )
        db.add(user)
    else:
        user.username = payload.username
        user.full_name = payload.full_name

    if payload.mark_intro is not None:
        user.bot_intro_seen = payload.mark_intro

    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "tg_id": user.tg_id,
        "email": user.email,
        "bot_intro_seen": user.bot_intro_seen,
    }


@router.post("/bot/set-email")
def bot_set_email(
    payload: BotEmailAssign,
    _: None = Depends(require_bot_token),
    db: Session = Depends(get_db),
):
    if not payload.user_id and not payload.tg_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id or tg_id required")

    user = None
    if payload.user_id:
        user = db.get(User, payload.user_id)
    elif payload.tg_id:
        user = db.query(User).filter(User.tg_id == payload.tg_id).first()

    if not user and payload.tg_id:
        user = User(tg_id=payload.tg_id, role=UserRole.student)
        db.add(user)
        db.flush()
    elif not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    email_exists = db.query(User).filter(User.email == payload.email).first()
    if email_exists and email_exists.id != user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already in use")
    user.email = payload.email
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email}
