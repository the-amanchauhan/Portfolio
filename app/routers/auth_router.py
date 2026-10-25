from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from ..auth import DASHBOARD_PASSWORD

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "logged_in": False, "error": None})


@router.post("/login")
def login(request: Request, password: str = Form(...)):
    if password == DASHBOARD_PASSWORD:
        request.session["logged_in"] = True
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "logged_in": False, "error": "Wrong password"},
        status_code=401,
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/campaigns", status_code=302)
