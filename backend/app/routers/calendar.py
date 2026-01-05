from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from dateutil.rrule import rrulestr
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..config import APP_TZ
from ..database import get_db
from ..dependencies import get_current_user
from ..models import (
    CalendarEvent,
    ClubMember,
    ClubMemberRole,
    EventParticipant,
    EventStatus,
    EventType,
    Room,
    User,
    UserRole,
)
from ..schemas import EventCreate, EventOut

router = APIRouter(tags=["calendar"])


def _duration_from_minutes(minutes: Optional[int]) -> Optional[str]:
    if not minutes:
        return None
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def _to_event_out(event: CalendarEvent) -> EventOut:
    room_code = event.room.code if event.room else None
    return EventOut(
        id=str(event.id),
        title=event.title,
        start=event.starts_at,
        end=event.ends_at,
        rrule=event.rrule,
        duration=_duration_from_minutes(event.duration_minutes),
        event_type=event.event_type.value,
        status=event.status.value,
        room_id=event.room_id,
        room_code=room_code,
        club_id=event.club_id,
    )


def _expand_recurring_event(
    event: CalendarEvent,
    start: datetime,
    end: datetime,
) -> List[EventOut]:
    if not event.rrule:
        return [_to_event_out(event)]

    duration_minutes = event.duration_minutes
    if not duration_minutes and event.ends_at:
        duration_minutes = int((event.ends_at - event.starts_at).total_seconds() / 60)
    if not duration_minutes:
        duration_minutes = 60

    rule = rrulestr(event.rrule, dtstart=event.starts_at)
    duration = timedelta(minutes=duration_minutes)
    occurrences = []

    for occ_start in rule.between(start, end, inc=True):
        occ_end = occ_start + duration
        occurrences.append(
            EventOut(
                id=f"{event.id}:{occ_start.isoformat()}",
                title=event.title,
                start=occ_start,
                end=occ_end,
                rrule=None,
                duration=None,
                event_type=event.event_type.value,
                status=event.status.value,
                room_id=event.room_id,
                room_code=event.room.code if event.room else None,
                club_id=event.club_id,
            )
        )

    return occurrences


@router.get("/calendar/events", response_model=List[EventOut])
def list_events(
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(CalendarEvent)

    if user.role == UserRole.admin:
        pass
    elif user.role == UserRole.club_leader:
        club_ids = (
            db.query(ClubMember.club_id)
            .filter(
                ClubMember.user_id == user.id,
                ClubMember.role == ClubMemberRole.leader,
            )
            .all()
        )
        club_ids = [cid for (cid,) in club_ids]
        if not club_ids:
            return []
        query = query.filter(CalendarEvent.club_id.in_(club_ids))
    else:
        query = (
            query.join(EventParticipant)
            .filter(EventParticipant.user_id == user.id)
            .filter(CalendarEvent.status == EventStatus.approved)
        )

    if start and end:
        non_recurring = and_(
            CalendarEvent.rrule.is_(None),
            CalendarEvent.starts_at < end,
        )
        query = query.filter(or_(CalendarEvent.rrule.is_not(None), non_recurring))

    events = query.order_by(CalendarEvent.starts_at.desc()).all()
    results: List[EventOut] = []

    for event in events:
        if event.rrule and start and end:
            results.extend(_expand_recurring_event(event, start, end))
        else:
            results.append(_to_event_out(event))

    return results


@router.post("/calendar/events", response_model=EventOut)
def create_event(
    payload: EventCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        event_type = EventType(payload.event_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid event type")

    if event_type == EventType.lesson and user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin required for lessons")

    if payload.rrule and not payload.duration_minutes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="duration_minutes required for recurring events",
        )
    if not payload.rrule and not payload.ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ends_at required for one-off events",
        )

    if user.role == UserRole.club_leader:
        if not payload.club_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="club_id required")
        club_ok = (
            db.query(ClubMember)
            .filter(
                ClubMember.user_id == user.id,
                ClubMember.club_id == payload.club_id,
                ClubMember.role == ClubMemberRole.leader,
            )
            .first()
        )
        if not club_ok:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not a club leader")
        status_value = EventStatus.pending
    else:
        status_value = EventStatus.approved

    room_id = payload.room_id
    if payload.room_code:
        room = db.query(Room).filter(Room.code.ilike(payload.room_code.strip())).first()
        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="room not found")
        room_id = room.id

    event = CalendarEvent(
        title=payload.title,
        description=payload.description,
        event_type=event_type,
        status=status_value,
        room_id=room_id,
        club_id=payload.club_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        rrule=payload.rrule,
        duration_minutes=payload.duration_minutes,
        timezone=payload.timezone or APP_TZ,
        created_by=user.id,
    )

    db.add(event)
    db.flush()

    if payload.participant_ids and user.role == UserRole.admin:
        for participant_id in payload.participant_ids:
            db.add(EventParticipant(event_id=event.id, user_id=participant_id))

    db.commit()
    db.refresh(event)
    return _to_event_out(event)


@router.patch("/calendar/events/{event_id}/cancel", response_model=EventOut)
def cancel_event(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = db.get(CalendarEvent, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event not found")

    if user.role != UserRole.admin and event.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    event.status = EventStatus.cancelled
    db.commit()
    db.refresh(event)
    return _to_event_out(event)
