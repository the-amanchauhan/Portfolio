import time
import datetime
from fastapi import APIRouter, Request, Form, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import get_db, SessionLocal
from ..models import Campaign, CampaignRecipient, Contact, Template, gen_tracking_code
from ..auth import require_login
from .. import meta_api

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/campaigns", response_class=HTMLResponse)
def list_campaigns(request: Request, db: Session = Depends(get_db)):
    if (resp := require_login(request)):
        return resp
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    tpls = db.query(Template).filter(Template.status == "APPROVED").all()
    contact_count = db.query(Contact).count()
    return templates.TemplateResponse(
        "campaigns.html",
        {"request": request, "logged_in": True, "campaigns": campaigns,
         "templates": tpls, "contact_count": contact_count},
    )


@router.post("/campaigns/create")
def create_campaign(
    request: Request, background_tasks: BackgroundTasks,
    name: str = Form(...), template_id: int = Form(...),
    db: Session = Depends(get_db),
):
    if (resp := require_login(request)):
        return resp
    campaign = Campaign(name=name, template_id=template_id, status="sending")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    contacts = db.query(Contact).all()
    tpl = db.query(Template).filter(Template.id == template_id).first()
    for c in contacts:
        code = gen_tracking_code() if tpl.has_url_button else ""
        db.add(CampaignRecipient(
            campaign_id=campaign.id, contact_id=c.id, phone=c.phone,
            name=c.name, status="queued", tracking_code=code,
        ))
    db.commit()

    background_tasks.add_task(run_campaign, campaign.id)
    return RedirectResponse(url=f"/campaigns/{campaign.id}", status_code=302)


def run_campaign(campaign_id: int):
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        tpl = db.query(Template).filter(Template.id == campaign.template_id).first()
        recipients = db.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == campaign_id, CampaignRecipient.status == "queued"
        ).all()
        for r in recipients:
            body_params = [r.name or "there"] if tpl.variable_count >= 1 else []
            # pad extra variables with blank placeholders if the template needs more than 1
            while len(body_params) < tpl.variable_count:
                body_params.append("")
            button_param = r.tracking_code if tpl.has_url_button else None
            ok, wamid, err = meta_api.send_template_message(
                r.phone, tpl.name, tpl.language, body_params, button_param,
            )
            r.status = "sent" if ok else "failed"
            r.wamid = wamid or ""
            r.error = err or ""
            r.sent_at = datetime.datetime.utcnow()
            db.commit()
            time.sleep(1.2)
        campaign.status = "done"
        db.commit()
    finally:
        db.close()


@router.get("/campaigns/{campaign_id}", response_class=HTMLResponse)
def campaign_detail(request: Request, campaign_id: int, db: Session = Depends(get_db)):
    if (resp := require_login(request)):
        return resp
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    recipients = db.query(CampaignRecipient).filter(CampaignRecipient.campaign_id == campaign_id).all()
    stats = {
        "total": len(recipients),
        "sent": sum(1 for r in recipients if r.status in ("sent", "delivered", "read")),
        "delivered": sum(1 for r in recipients if r.status in ("delivered", "read")),
        "read": sum(1 for r in recipients if r.status == "read"),
        "failed": sum(1 for r in recipients if r.status == "failed"),
        "clicked": sum(1 for r in recipients if r.clicked_at is not None),
    }
    return templates.TemplateResponse(
        "campaign_detail.html",
        {"request": request, "logged_in": True, "campaign": campaign,
         "recipients": recipients, "stats": stats},
    )
