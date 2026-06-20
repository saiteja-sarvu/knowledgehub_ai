import os
import re

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AUTH_COOKIE_NAME,
    create_access_token,
    get_user_from_request,
    hash_password,
    verify_password
)
from app.database.db import get_db
from app.database.models import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def render_auth_template(request, template_name, error=None, values=None):
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "error": error,
            "values": values or {}
        },
        status_code=status.HTTP_400_BAD_REQUEST if error else status.HTTP_200_OK
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    if get_user_from_request(request, db):
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_auth_template(request, "login.html")


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not verify_password(password, user.password):
        return render_auth_template(
            request,
            "login.html",
            "Invalid email or password.",
            {"email": normalized_email}
        )

    response = RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        AUTH_COOKIE_NAME,
        create_access_token(user.id),
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true"
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    if get_user_from_request(request, db):
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return render_auth_template(request, "register.html")


@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    clean_name = name.strip()
    normalized_email = email.strip().lower()
    values = {"name": clean_name, "email": normalized_email}

    if len(clean_name) < 2:
        return render_auth_template(request, "register.html", "Enter your full name.", values)
    if not EMAIL_PATTERN.match(normalized_email):
        return render_auth_template(request, "register.html", "Enter a valid email address.", values)
    if len(password) < 8:
        return render_auth_template(request, "register.html", "Password must be at least 8 characters.", values)
    if len(password.encode("utf-8")) > 72:
        return render_auth_template(request, "register.html", "Password must be 72 bytes or fewer.", values)
    if password != confirm_password:
        return render_auth_template(request, "register.html", "Passwords do not match.", values)
    if db.query(User).filter(User.email == normalized_email).first():
        return render_auth_template(request, "register.html", "An account with this email already exists.", values)

    user = User(
        name=clean_name,
        email=normalized_email,
        password=hash_password(password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    response = RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        AUTH_COOKIE_NAME,
        create_access_token(user.id),
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true"
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(AUTH_COOKIE_NAME)
    return response

@router.get("/test")
def test():
    return {
        "message": "Auth routes working"
    }
