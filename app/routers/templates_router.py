from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Template
from ..auth import require_login
from .. import meta_api

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/templates-page", response_class=HTMLResponse)
def list_templates_page(request: Request, db: Session = Depends(get_db), error: str = None):
    if (resp := require_login(request)):
        return resp
    tpls = db.query(Template).order_by(Template.updated_at.desc()).all()
    return templates.TemplateResponse(
        "templates.html",
        {"request": request, "logged_in": True, "templates": tpls, "error": error},
    )


@router.post("/templates-page/sync")
def sync_templates(request: Request, db: Session = Depends(get_db)):
    if (resp := require_login(request)):
        return resp
    ok, data, err = meta_api.list_templates()
    if not ok:
        return RedirectResponse(url=f"/templates-page?error={err}", status_code=302)
    for t in data:
        name = t.get("name")
        language = t.get("language")
        existing = db.query(Template).filter(Template.name == name, Template.language == language).first()
        body_text = ""
        var_count = 0
        has_url = False
        url_base = ""
        for comp in t.get("components", []):
            if comp.get("type") == "BODY":
                body_text = comp.get("text", "")
                var_count = body_text.count("{{")
            if comp.get("type") == "BUTTONS":
                for b in comp.get("buttons", []):
                    if b.get("type") == "URL":
                        has_url = True
                        url_base = b.get("url", "")
        if existing:
            existing.status = t.get("status", "")
            existing.category = t.get("category", "")
            existing.body_text = body_text
            existing.variable_count = var_count
            existing.has_url_button = has_url
            existing.url_button_base = url_base
            existing.meta_template_id = t.get("id", "")
        else:
            db.add(Template(
                name=name, language=language, category=t.get("category", ""),
                status=t.get("status", ""), body_text=body_text,
                variable_count=var_count, has_url_button=has_url,
                url_button_base=url_base, meta_template_id=t.get("id", ""),
            ))
    db.commit()
    return RedirectResponse(url="/templates-page", status_code=302)


@router.post("/templates-page/create")
def create_template(
    request: Request,
    name: str = Form(...),
    language: str = Form("en_US"),
    category: str = Form("UTILITY"),
    body_text: str = Form(...),
    button_text: str = Form(""),
    button_url: str = Form(""),
    redirect_target: str = Form(""),
    db: Session = Depends(get_db),
):
    if (resp := require_login(request)):
        return resp
    ok, tpl_id, err = meta_api.create_template(
        name, language, category, body_text,
        button_text or None, button_url or None,
    )
    if not ok:
        return RedirectResponse(url=f"/templates-page?error={err}", status_code=302)
    var_count = body_text.count("{{")
    db.add(Template(
        name=name, language=language, category=category, status="PENDING",
        body_text=body_text, variable_count=var_count,
        has_url_button=bool(button_url), url_button_base=button_url,
        redirect_target=redirect_target,
        meta_template_id=tpl_id or "",
    ))
    db.commit()
    return RedirectResponse(url="/templates-page", status_code=302)
