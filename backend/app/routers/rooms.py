from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Room, User
from ..schemas import RoomOut

router = APIRouter(tags=["rooms"])


@router.get("/rooms/available", response_model=List[RoomOut])
def list_available_rooms(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rooms = db.query(Room).filter(Room.is_active.is_(True)).order_by(Room.code.asc()).all()
    return [RoomOut.model_validate(room) for room in rooms]
