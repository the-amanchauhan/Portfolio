# WhatsApp Campaign Dashboard

A small self-hosted web dashboard for sending WhatsApp template messages
directly through Meta's Cloud API (no BSP), managing contacts, creating
templates, and tracking delivery / read / link-click status via Meta's
webhooks.

## Features
- **Contacts**: add manually or import from an Excel file
- **Templates**: sync existing approved templates from your WABA, or create
  and submit new ones for Meta's review, directly from the dashboard
- **Campaigns**: pick a template, send to your whole contact list in one
  click, watch live status (sent / delivered / read / failed)
- **Link click tracking**: templates with a URL button route through this
  app's own `/r/<code>` redirect, so you can see who actually clicked

## Deploying (Render, free tier)

1. Push this repo to your own GitHub account (or use it as-is if Claude
   already did this for you).
2. Go to https://render.com -> New -> Blueprint -> connect this repo.
   Render will read `render.yaml` and set up the web service + a free
   Postgres database automatically.
3. When prompted, fill in the environment variables it asks for:
   - `DASHBOARD_PASSWORD` - the password you'll use to log into the dashboard
   - `WHATSAPP_ACCESS_TOKEN` - your System User permanent token
   - `WHATSAPP_PHONE_NUMBER_ID` - your WhatsApp phone number ID
   - `WHATSAPP_WABA_ID` - your WhatsApp Business Account ID
   - `WHATSAPP_WEBHOOK_VERIFY_TOKEN` - make up any string, you'll reuse it in step 5
4. Deploy. Render gives you a public URL like `https://wa-dashboard-xxxx.onrender.com`.
5. In Meta Developer Console -> your App -> WhatsApp -> Configuration -> Webhooks:
   - Callback URL: `https://wa-dashboard-xxxx.onrender.com/webhook`
   - Verify token: the same `WHATSAPP_WEBHOOK_VERIFY_TOKEN` value from step 3
   - Subscribe to the `messages` field (this covers delivery/read status and inbound replies)
6. Open your dashboard URL, log in with `DASHBOARD_PASSWORD`, go to
   **Templates -> Sync from Meta** to pull in your existing approved templates.

## Local testing (optional)

```
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://localhost:8000. Note: webhooks (delivery/read/click tracking)
only work once the app is publicly reachable (i.e. deployed), since Meta
needs to be able to reach it over the internet.
