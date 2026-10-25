import os
import json
import datetime
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, JSONResponse

from ..db import SessionLocal
from ..models import CampaignRecipient, WebhookEvent

router = APIRouter()

VERIFY_TOKEN = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "changeme-verify-token")


@router.get("/webhook")
def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge or "")
    return PlainTextResponse("verification failed", status_code=403)


@router.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.json()
    db = SessionLocal()
    try:
        db.add(WebhookEvent(event_type="raw", payload=json.dumps(body)[:8000]))
        db.commit()

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                for status in value.get("statuses", []):
                    wamid = status.get("id")
                    state = status.get("status")  # sent, delivered, read, failed
                    ts = status.get("timestamp")
                    when = datetime.datetime.utcfromtimestamp(int(ts)) if ts else datetime.datetime.utcnow()
                    rec = db.query(CampaignRecipient).filter(CampaignRecipient.wamid == wamid).first()
                    if rec:
                        if state == "delivered" and rec.status != "read":
                            rec.status = "delivered"
                            rec.delivered_at = when
                        elif state == "read":
                            rec.status = "read"
                            rec.read_at = when
                        elif state == "failed":
                            rec.status = "failed"
                            errs = status.get("errors", [])
                            if errs:
                                rec.error = errs[0].get("title", "failed")
                        db.commit()

                for msg in value.get("messages", []):
                    # Inbound message (e.g. quick-reply button tap). Logged for now.
                    db.add(WebhookEvent(
                        event_type="inbound_message",
                        wamid=msg.get("id", ""),
                        payload=json.dumps(msg)[:4000],
                    ))
                    db.commit()
    finally:
        db.close()
    return JSONResponse({"ok": True})
