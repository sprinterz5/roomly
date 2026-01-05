from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_admin
from ..models import (
    CalendarEvent,
    Club,
    ClubMember,
    ClubMemberRole,
    EventParticipant,
    EventStatus,
    Room,
    User,
    UserRole,
)
from ..schemas import (
    AdminClubMemberOut,
    AdminClubOut,
    AdminClubLeaderAssign,
    AdminEventOut,
    AdminEventParticipantOut,
    AdminRoleAssign,
    AdminUserOut,
    ClubCreate,
    ClubLeaderAssign,
    RoleAssign,
    RoomCreate,
    RoomOut,
    RoomUpdate,
)

router = APIRouter(tags=["admin"])


@router.post("/admin/users/{user_id}/role")
def assign_role(
    user_id: int,
    payload: RoleAssign,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        role = UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid role")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    user.role = role
    db.commit()
    db.refresh(user)
    return {"id": user.id, "role": user.role.value}


@router.post("/admin/users/role")
def assign_role_by_email(
    payload: AdminRoleAssign,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        role = UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid role")

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    user.role = role
    db.commit()
    db.refresh(user)
    return {"id": user.id, "role": user.role.value}


@router.get("/admin/users", response_model=list[AdminUserOut])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.id.asc()).all()
    return [
        AdminUserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
        )
        for user in users
    ]


@router.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    db.query(CalendarEvent).filter(CalendarEvent.approved_by == user.id).update(
        {CalendarEvent.approved_by: None}
    )

    event_ids = [eid for (eid,) in db.query(CalendarEvent.id).filter(CalendarEvent.created_by == user.id).all()]
    if event_ids:
        db.query(EventParticipant).filter(EventParticipant.event_id.in_(event_ids)).delete(
            synchronize_session=False
        )
        db.query(CalendarEvent).filter(CalendarEvent.id.in_(event_ids)).delete(
            synchronize_session=False
        )

    db.query(EventParticipant).filter(EventParticipant.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(ClubMember).filter(ClubMember.user_id == user.id).delete(synchronize_session=False)
    db.query(Club).filter(Club.owner_user_id == user.id).update({Club.owner_user_id: None})

    db.delete(user)
    db.commit()
    return {"id": user_id, "status": "deleted"}


@router.post("/admin/clubs")
def create_club(
    payload: ClubCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    owner_id = payload.owner_user_id
    if payload.owner_email:
        owner = db.query(User).filter(User.email.ilike(payload.owner_email)).first()
        if not owner:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="owner not found")
        owner_id = owner.id

    club = Club(name=payload.name, owner_user_id=owner_id)
    db.add(club)
    db.commit()
    db.refresh(club)
    return {"id": club.id, "name": club.name}


@router.get("/admin/clubs", response_model=list[AdminClubOut])
def list_clubs(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    clubs = db.query(Club).order_by(Club.name.asc()).all()
    return [
        AdminClubOut(id=club.id, name=club.name, owner_user_id=club.owner_user_id)
        for club in clubs
    ]


@router.delete("/admin/clubs/{club_id}")
def delete_club(
    club_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="club not found")

    event_ids = [eid for (eid,) in db.query(CalendarEvent.id).filter(CalendarEvent.club_id == club.id).all()]
    if event_ids:
        db.query(EventParticipant).filter(EventParticipant.event_id.in_(event_ids)).delete(
            synchronize_session=False
        )
        db.query(CalendarEvent).filter(CalendarEvent.id.in_(event_ids)).delete(
            synchronize_session=False
        )

    db.query(ClubMember).filter(ClubMember.club_id == club.id).delete(synchronize_session=False)

    db.delete(club)
    db.commit()
    return {"id": club_id, "status": "deleted"}


@router.post("/admin/clubs/{club_id}/leaders")
def assign_club_leader(
    club_id: int,
    payload: ClubLeaderAssign,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="club not found")

    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    membership = (
        db.query(ClubMember)
        .filter(ClubMember.club_id == club_id, ClubMember.user_id == user.id)
        .first()
    )
    if not membership:
        membership = ClubMember(club_id=club_id, user_id=user.id, role=ClubMemberRole.leader)
        db.add(membership)
    else:
        membership.role = ClubMemberRole.leader

    if user.role != UserRole.admin:
        user.role = UserRole.club_leader

    db.commit()
    return {"club_id": club_id, "user_id": user.id, "role": membership.role.value}


@router.get("/admin/club-members", response_model=list[AdminClubMemberOut])
def list_club_members_admin(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ClubMember, Club, User)
        .join(Club, Club.id == ClubMember.club_id)
        .join(User, User.id == ClubMember.user_id)
        .order_by(Club.name.asc(), User.email.asc())
        .all()
    )
    return [
        AdminClubMemberOut(
            club_id=club.id,
            club_name=club.name,
            user_id=member.user_id,
            user_email=user.email,
            role=member.role.value,
        )
        for member, club, user in rows
    ]


@router.delete("/admin/club-members")
def delete_club_member(
    club_id: int,
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(ClubMember)
        .filter(ClubMember.club_id == club_id, ClubMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="membership not found")

    db.delete(membership)
    db.commit()
    return {"club_id": club_id, "user_id": user_id, "status": "deleted"}


@router.post("/admin/clubs/leader")
def assign_club_leader_by_name(
    payload: AdminClubLeaderAssign,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    club = db.query(Club).filter(Club.name.ilike(payload.club_name)).first()
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="club not found")

    user = db.query(User).filter(User.email.ilike(payload.user_email)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    membership = (
        db.query(ClubMember)
        .filter(ClubMember.club_id == club.id, ClubMember.user_id == user.id)
        .first()
    )
    if not membership:
        membership = ClubMember(club_id=club.id, user_id=user.id, role=ClubMemberRole.leader)
        db.add(membership)
    else:
        membership.role = ClubMemberRole.leader

    if user.role != UserRole.admin:
        user.role = UserRole.club_leader

    db.commit()
    return {"club_id": club.id, "user_id": user.id, "role": membership.role.value}


@router.post("/admin/events/{event_id}/approve")
def approve_event(
    event_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = db.get(CalendarEvent, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event not found")

    event.status = EventStatus.approved
    event.approved_by = admin.id
    event.approved_at = datetime.utcnow()
    db.commit()
    return {"id": event.id, "status": event.status.value}


@router.get("/admin/events", response_model=list[AdminEventOut])
def list_events_admin(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(CalendarEvent, Room.code)
        .outerjoin(Room, Room.id == CalendarEvent.room_id)
        .order_by(CalendarEvent.starts_at.desc())
        .all()
    )
    return [
        AdminEventOut(
            id=event.id,
            title=event.title,
            status=event.status.value,
            event_type=event.event_type.value,
            club_id=event.club_id,
            room_code=room_code,
        )
        for event, room_code in rows
    ]


@router.delete("/admin/events/{event_id}")
def delete_event(
    event_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = db.get(CalendarEvent, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event not found")

    db.query(EventParticipant).filter(EventParticipant.event_id == event_id).delete(
        synchronize_session=False
    )
    db.delete(event)
    db.commit()
    return {"id": event_id, "status": "deleted"}


@router.get("/admin/rooms", response_model=list[RoomOut])
def list_rooms(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rooms = db.query(Room).order_by(Room.code.asc()).all()
    return [RoomOut.model_validate(room) for room in rooms]


@router.post("/admin/rooms", response_model=RoomOut)
def create_room(
    payload: RoomCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(Room).filter(Room.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="room code exists")

    room = Room(
        code=payload.code,
        building=payload.building,
        floor=payload.floor,
        room_type=payload.room_type,
        capacity=payload.capacity,
        is_active=payload.is_active if payload.is_active is not None else True,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return RoomOut.model_validate(room)


@router.patch("/admin/rooms/{room_code}", response_model=RoomOut)
def update_room(
    room_code: str,
    payload: RoomUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="room not found")

    if payload.building is not None:
        room.building = payload.building
    if payload.floor is not None:
        room.floor = payload.floor
    if payload.room_type is not None:
        room.room_type = payload.room_type
    if payload.capacity is not None:
        room.capacity = payload.capacity
    if payload.is_active is not None:
        room.is_active = payload.is_active

    db.commit()
    db.refresh(room)
    return RoomOut.model_validate(room)


@router.delete("/admin/rooms/{room_code}")
def delete_room(
    room_code: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    room = db.query(Room).filter(Room.code == room_code).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="room not found")

    db.query(CalendarEvent).filter(CalendarEvent.room_id == room.id).update(
        {CalendarEvent.room_id: None}
    )
    db.delete(room)
    db.commit()
    return {"code": room_code, "status": "deleted"}


@router.post("/admin/events/{event_id}/reject")
def reject_event(
    event_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = db.get(CalendarEvent, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event not found")

    event.status = EventStatus.rejected
    event.approved_by = admin.id
    event.approved_at = datetime.utcnow()
    db.commit()
    return {"id": event.id, "status": event.status.value}


@router.get("/admin/event-participants", response_model=list[AdminEventParticipantOut])
def list_event_participants_admin(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(EventParticipant, User)
        .join(User, User.id == EventParticipant.user_id)
        .order_by(EventParticipant.event_id.asc(), User.email.asc())
        .all()
    )
    return [
        AdminEventParticipantOut(
            event_id=participant.event_id,
            user_id=participant.user_id,
            user_email=user.email,
        )
        for participant, user in rows
    ]


@router.delete("/admin/event-participants")
def delete_event_participant(
    event_id: int,
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    participant = (
        db.query(EventParticipant)
        .filter(EventParticipant.event_id == event_id, EventParticipant.user_id == user_id)
        .first()
    )
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="participant not found")

    db.delete(participant)
    db.commit()
    return {"event_id": event_id, "user_id": user_id, "status": "deleted"}
