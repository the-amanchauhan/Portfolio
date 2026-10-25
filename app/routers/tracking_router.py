import datetime
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from ..db import SessionLocal
from ..models import CampaignRecipient, Campaign, Template

router = APIRouter()


@router.get("/r/{code}")
def track_click(code: str):
    db = SessionLocal()
    try:
        rec = db.query(CampaignRecipient).filter(CampaignRecipient.tracking_code == code).first()
        if not rec:
            return RedirectResponse(url="https://net2success.com", status_code=302)
        if rec.clicked_at is None:
            rec.clicked_at = datetime.datetime.utcnow()
            db.commit()
        campaign = db.query(Campaign).filter(Campaign.id == rec.campaign_id).first()
        tpl = db.query(Template).filter(Template.id == campaign.template_id).first() if campaign else None
        target = (tpl.redirect_target if tpl and tpl.redirect_target else "") or "https://net2success.com"
        return RedirectResponse(url=target, status_code=302)
    finally:
        db.close()
