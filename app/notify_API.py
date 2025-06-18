from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.notify_utils import notify_applicants

router = APIRouter()


class NotificationItem(BaseModel):
    applicant_phone: str
    message: str


class NotificationRequest(BaseModel):
    notifications: list[NotificationItem]


@router.post("/notify")
async def notify_users(payload: NotificationRequest):
    failed = await notify_applicants([item.dict() for item in payload.notifications])
    if failed:
        raise HTTPException(status_code=207, detail={"failed_phones": failed})
    return {"status": "ok"}
