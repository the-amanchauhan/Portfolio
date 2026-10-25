import datetime
import secrets

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship

from .db import Base


def now():
    return datetime.datetime.utcnow()


class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True)
    phone = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(255), default="")
    extra = Column(Text, default="")  # JSON string for extra template variables
    created_at = Column(DateTime, default=now)


class Template(Base):
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    language = Column(String(16), default="en_US")
    category = Column(String(32), default="UTILITY")
    status = Column(String(32), default="PENDING")  # synced from Meta
    body_text = Column(Text, default="")
    variable_count = Column(Integer, default=0)
    has_url_button = Column(Boolean, default=False)
    url_button_base = Column(String(512), default="")  # static part of the URL, {{1}} appended as tracking code
    redirect_target = Column(String(1024), default="")  # where /r/<code> ultimately sends the recipient
    meta_template_id = Column(String(64), default="")
    updated_at = Column(DateTime, default=now, onupdate=now)


class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    template_id = Column(Integer, ForeignKey("templates.id"))
    status = Column(String(32), default="draft")  # draft, sending, done
    created_at = Column(DateTime, default=now)

    template = relationship("Template")


class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    phone = Column(String(32), index=True)
    name = Column(String(255), default="")
    status = Column(String(32), default="queued")  # queued, sent, delivered, read, failed
    wamid = Column(String(128), default="", index=True)
    error = Column(Text, default="")
    tracking_code = Column(String(32), default="", index=True)
    clicked_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    campaign = relationship("Campaign")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id = Column(Integer, primary_key=True)
    event_type = Column(String(64))
    wamid = Column(String(128), index=True, default="")
    payload = Column(Text)
    received_at = Column(DateTime, default=now)


def gen_tracking_code():
    return secrets.token_urlsafe(6).replace("-", "a").replace("_", "b")[:8]
