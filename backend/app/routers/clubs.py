from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Club, ClubMember, ClubMemberRole, User, UserRole
from ..schemas import ClubMemberAdd, ClubMemberUserOut, ClubMembershipOut, ClubOut

router = APIRouter(tags=["clubs"])


@router.get("/clubs/my", response_model=List[ClubOut])
def list_my_clubs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == UserRole.admin:
        clubs = db.query(Club).order_by(Club.name.asc()).all()
        return [ClubOut.model_validate(club) for club in clubs]

    if user.role != UserRole.club_leader:
        return []

    clubs = (
        db.query(Club)
        .join(ClubMember, ClubMember.club_id == Club.id)
        .filter(
            ClubMember.user_id == user.id,
            ClubMember.role == ClubMemberRole.leader,
        )
        .order_by(Club.name.asc())
        .all()
    )
    return [ClubOut.model_validate(club) for club in clubs]


@router.get("/clubs/memberships", response_model=List[ClubMembershipOut])
def list_memberships(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memberships = (
        db.query(Club, ClubMember.role)
        .join(ClubMember, ClubMember.club_id == Club.id)
        .filter(ClubMember.user_id == user.id)
        .order_by(Club.name.asc())
        .all()
    )

    return [
        ClubMembershipOut(id=club.id, name=club.name, role=role.value)
        for club, role in memberships
    ]


@router.post("/clubs/members", response_model=ClubMembershipOut)
def add_member(
    payload: ClubMemberAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    club = db.query(Club).filter(Club.name.ilike(payload.club_name.strip())).first()
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="club not found")

    target = db.query(User).filter(User.email.ilike(payload.user_email.strip())).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    if user.role != UserRole.admin:
        if user.role != UserRole.club_leader:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="club leader required")

        leader = (
            db.query(ClubMember)
            .filter(
                ClubMember.user_id == user.id,
                ClubMember.club_id == club.id,
                ClubMember.role == ClubMemberRole.leader,
            )
            .first()
        )
        if not leader:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not a leader for this club")

    membership = (
        db.query(ClubMember)
        .filter(ClubMember.club_id == club.id, ClubMember.user_id == target.id)
        .first()
    )
    if not membership:
        membership = ClubMember(
            club_id=club.id,
            user_id=target.id,
            role=ClubMemberRole.member,
        )
        db.add(membership)

    db.commit()
    return ClubMembershipOut(id=club.id, name=club.name, role=membership.role.value)


@router.delete("/clubs/members")
def leave_club(
    club_name: str = Query(..., min_length=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    club = db.query(Club).filter(Club.name.ilike(club_name.strip())).first()
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="club not found")

    membership = (
        db.query(ClubMember)
        .filter(ClubMember.club_id == club.id, ClubMember.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="membership not found")

    if membership.role == ClubMemberRole.leader:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="leader cannot leave club")

    db.delete(membership)
    db.commit()
    return {"club_name": club.name, "status": "left"}


@router.get("/clubs/members", response_model=List[ClubMemberUserOut])
def list_club_members(
    club_name: str = Query(..., min_length=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    club = db.query(Club).filter(Club.name.ilike(club_name.strip())).first()
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="club not found")

    if user.role != UserRole.admin:
        leader = (
            db.query(ClubMember)
            .filter(
                ClubMember.user_id == user.id,
                ClubMember.club_id == club.id,
                ClubMember.role == ClubMemberRole.leader,
            )
            .first()
        )
        if not leader:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not a leader for this club")

    members = (
        db.query(User, ClubMember.role)
        .join(ClubMember, ClubMember.user_id == User.id)
        .filter(ClubMember.club_id == club.id)
        .order_by(User.full_name.asc(), User.email.asc())
        .all()
    )

    return [
        ClubMemberUserOut(
            email=member.email,
            full_name=member.full_name,
            role=role.value,
        )
        for member, role in members
    ]
