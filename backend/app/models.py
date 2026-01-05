import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(enum.Enum):
    student = "student"
    club_leader = "club_leader"
    admin = "admin"


class ClubMemberRole(enum.Enum):
    member = "member"
    leader = "leader"


class EventType(enum.Enum):
    lesson = "lesson"
    event = "event"


class EventStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64))
    full_name: Mapped[Optional[str]] = mapped_column(String(128))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student)
    bot_intro_seen: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    club_memberships = relationship("ClubMember", back_populates="user")


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    members = relationship("ClubMember", back_populates="club")
    events = relationship("CalendarEvent", back_populates="club")


class ClubMember(Base):
    __tablename__ = "club_members"
    __table_args__ = (UniqueConstraint("club_id", "user_id", name="uq_club_member"),)

    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[ClubMemberRole] = mapped_column(Enum(ClubMemberRole), default=ClubMemberRole.member)

    club = relationship("Club", back_populates="members")
    user = relationship("User", back_populates="club_memberships")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    building: Mapped[Optional[str]] = mapped_column(String(64))
    floor: Mapped[Optional[str]] = mapped_column(String(32))
    room_type: Mapped[Optional[str]] = mapped_column(String(64))
    capacity: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    events = relationship("CalendarEvent", back_populates="room")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType))
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.pending)

    room_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rooms.id"))
    club_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clubs.id"))

    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rrule: Mapped[Optional[str]] = mapped_column(Text)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    timezone: Mapped[Optional[str]] = mapped_column(String(64))

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    room = relationship("Room", back_populates="events")
    club = relationship("Club", back_populates="events")
    participants = relationship("EventParticipant", back_populates="event")

    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])


class EventParticipant(Base):
    __tablename__ = "event_participants"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_participant"),)

    event_id: Mapped[int] = mapped_column(ForeignKey("calendar_events.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)

    event = relationship("CalendarEvent", back_populates="participants")
    user = relationship("User")
