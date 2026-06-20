from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.security import get_user_from_request
from app.database.db import get_db
from app.database.models import ChatHistory, Document


router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

    documents = (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.uploaded_at.desc())
        .limit(5)
        .all()
    )
    chat_count = db.query(ChatHistory).filter(ChatHistory.user_id == user.id).count()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "documents": documents,
            "chat_count": chat_count
        }
    )
