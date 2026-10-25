import os
import requests

ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WABA_ID = os.environ.get("WHATSAPP_WABA_ID", "")
API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")

BASE = f"https://graph.facebook.com/{API_VERSION}"


def _headers():
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def send_template_message(phone, template_name, language, body_params, button_param=None):
    """Sends one template message. body_params: list of strings for the body
    component (in order). button_param: optional single string for a dynamic
    URL button's {{1}} suffix. Returns (ok, wamid_or_None, error_or_None)."""
    components = []
    if body_params:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in body_params],
        })
    if button_param is not None:
        components.append({
            "type": "button",
            "sub_type": "url",
            "index": "0",
            "parameters": [{"type": "text", "text": button_param}],
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": components,
        },
    }
    try:
        resp = requests.post(
            f"{BASE}/{PHONE_NUMBER_ID}/messages",
            headers=_headers(), json=payload, timeout=30,
        )
    except requests.RequestException as e:
        return False, None, f"network error: {e}"

    try:
        data = resp.json()
    except ValueError:
        return False, None, f"non-JSON response ({resp.status_code}): {resp.text[:300]}"

    if resp.status_code == 200 and "messages" in data:
        return True, data["messages"][0].get("id"), None

    err = data.get("error", {})
    msg = err.get("message", "unknown error")
    code = err.get("code", resp.status_code)
    subcode = err.get("error_subcode")
    detail = f"[{code}" + (f"/{subcode}" if subcode else "") + f"] {msg}"
    return False, None, detail


def list_templates():
    """Fetch message templates from the WABA. Requires WHATSAPP_WABA_ID."""
    if not WABA_ID:
        return False, [], "WHATSAPP_WABA_ID is not set"
    try:
        resp = requests.get(
            f"{BASE}/{WABA_ID}/message_templates",
            headers=_headers(), params={"limit": 100}, timeout=30,
        )
        data = resp.json()
    except Exception as e:
        return False, [], str(e)
    if resp.status_code != 200:
        err = data.get("error", {}).get("message", "unknown error")
        return False, [], err
    return True, data.get("data", []), None


def create_template(name, language, category, body_text, button_text=None, button_url=None):
    """Create a new template on the WABA and submit for review."""
    if not WABA_ID:
        return False, None, "WHATSAPP_WABA_ID is not set"
    components = []
    if "{{1}}" in body_text or "{{" in body_text:
        example_body = body_text
        n = 1
        while f"{{{{{n}}}}}" in example_body:
            example_body = example_body.replace(f"{{{{{n}}}}}", f"example{n}")
            n += 1
        components.append({
            "type": "BODY",
            "text": body_text,
            "example": {"body_text": [[
                f"example{i}" for i in range(1, n)
            ]]} if n > 1 else None,
        })
    else:
        components.append({"type": "BODY", "text": body_text})
    if button_text and button_url:
        button = {"type": "URL", "text": button_text, "url": button_url}
        if "{{1}}" in button_url:
            button["example"] = [button_url.replace("{{1}}", "example123")]
        components.append({"type": "BUTTONS", "buttons": [button]})
    # drop any None values (Meta rejects explicit nulls on some fields)
    components = [{k: v for k, v in c.items() if v is not None} for c in components]
    payload = {
        "name": name,
        "language": language,
        "category": category,
        "components": components,
    }
    try:
        resp = requests.post(
            f"{BASE}/{WABA_ID}/message_templates",
            headers=_headers(), json=payload, timeout=30,
        )
        data = resp.json()
    except Exception as e:
        return False, None, str(e)
    if resp.status_code not in (200, 201):
        err = data.get("error", {}).get("message", "unknown error")
        return False, None, err
    return True, data.get("id"), None
