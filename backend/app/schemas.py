from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuthRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    init_data: str = Field(..., alias="initData")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tg_id: str
    email: Optional[str]
    username: Optional[str]
    full_name: Optional[str]
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: str
    starts_at: datetime
    ends_at: Optional[datetime] = None
    rrule: Optional[str] = None
    duration_minutes: Optional[int] = None
    timezone: Optional[str] = None
    room_id: Optional[int] = None
    room_code: Optional[str] = None
    club_id: Optional[int] = None
    participant_ids: Optional[List[int]] = None


class EventOut(BaseModel):
    id: str
    title: str
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    rrule: Optional[str] = None
    duration: Optional[str] = None
    event_type: str
    status: str
    room_id: Optional[int] = None
    room_code: Optional[str] = None
    club_id: Optional[int] = None


class RoleAssign(BaseModel):
    role: str


class ClubCreate(BaseModel):
    name: str
    owner_user_id: Optional[int] = None
    owner_email: Optional[str] = None


class ClubLeaderAssign(BaseModel):
    user_id: int


class AdminRoleAssign(BaseModel):
    email: str
    role: str


class AdminClubLeaderAssign(BaseModel):
    club_name: str
    user_email: str


class RoomCreate(BaseModel):
    code: str
    building: Optional[str] = None
    floor: Optional[str] = None
    room_type: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = True


class RoomUpdate(BaseModel):
    building: Optional[str] = None
    floor: Optional[str] = None
    room_type: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    building: Optional[str]
    floor: Optional[str]
    room_type: Optional[str]
    capacity: Optional[int]
    is_active: bool


class AdminUserOut(BaseModel):
    id: int
    email: Optional[str]
    full_name: Optional[str]
    role: str


class AdminClubOut(BaseModel):
    id: int
    name: str
    owner_user_id: Optional[int]


class AdminClubMemberOut(BaseModel):
    club_id: int
    club_name: str
    user_id: int
    user_email: Optional[str]
    role: str


class AdminEventOut(BaseModel):
    id: int
    title: str
    status: str
    event_type: str
    club_id: Optional[int]
    room_code: Optional[str]


class AdminEventParticipantOut(BaseModel):
    event_id: int
    user_id: int
    user_email: Optional[str]


class ClubOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ClubMembershipOut(BaseModel):
    id: int
    name: str
    role: str


class ClubMemberAdd(BaseModel):
    club_name: str
    user_email: str


class ClubMemberUserOut(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str


class BotRoleAssign(BaseModel):
    user_id: Optional[int] = None
    tg_id: Optional[str] = None
    email: Optional[str] = None
    role: str


class BotClubLeaderAssign(BaseModel):
    club_id: Optional[int] = None
    club_name: Optional[str] = None
    user_id: Optional[int] = None
    tg_id: Optional[str] = None
    email: Optional[str] = None


class BotClubCreate(BaseModel):
    name: str
    owner_user_id: Optional[int] = None


class BotUserUpsert(BaseModel):
    tg_id: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    mark_intro: Optional[bool] = None


class BotEmailAssign(BaseModel):
    user_id: Optional[int] = None
    tg_id: Optional[str] = None
    email: str
