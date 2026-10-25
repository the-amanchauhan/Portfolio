from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
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
        header_type = "NONE"
        for comp in t.get("components", []):
            if comp.get("type") == "BODY":
                body_text = comp.get("text", "")
                var_count = body_text.count("{{")
            if comp.get("type") == "HEADER" and comp.get("format") == "IMAGE":
                header_type = "IMAGE"
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
            existing.header_type = header_type
        else:
            db.add(Template(
                name=name, language=language, category=t.get("category", ""),
                status=t.get("status", ""), body_text=body_text,
                variable_count=var_count, has_url_button=has_url,
                url_button_base=url_base, meta_template_id=t.get("id", ""),
                header_type=header_type,
            ))
    db.commit()
    return RedirectResponse(url="/templates-page", status_code=302)

@router.post("/templates-page/create")
async def create_template(
    request: Request,
    name: str = Form(...),
    language: str = Form("en_US"),
    category: str = Form("UTILITY"),
    body_text: str = Form(...),
    button_text: str = Form(""),
    button_url: str = Form(""),
    redirect_target: str = Form(""),
    header_type: str = Form("NONE"),
    header_image: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    if (resp := require_login(request)):
        return resp
    header_handle = None
    if header_type == "IMAGE" and header_image is not None and header_image.filename:
        content = await header_image.read()
        ok_u, header_handle, err_u = meta_api.upload_header_image_handle(
            content, header_image.filename, header_image.content_type or "image/jpeg",
        )
        if not ok_u:
            return RedirectResponse(url=f"/templates-page?error=Image+upload+failed:+{err_u}", status_code=302)
    ok, tpl_id, err = meta_api.create_template(
        name, language, category, body_text,
        button_text or None, button_url or None,
        header_type=header_type, header_handle=header_handle,
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
        header_type=header_type,
    ))
    db.commit()
    return RedirectResponse(url="/templates-page", status_code=302)

# end of templates_router.py
