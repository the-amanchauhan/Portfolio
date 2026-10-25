import os
import requests

ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WABA_ID = os.environ.get("WHATSAPP_WABA_ID", "")
APP_ID = os.environ.get("META_APP_ID", "")
API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")

BASE = f"https://graph.facebook.com/{API_VERSION}"

def _headers():
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

# Sends one template message. body_params: list of strings for the body
# component (in order). button_param: optional single string for a dynamic
# URL button's {{1}} suffix. header_image_link: optional public image URL
# for templates that have an IMAGE header. Returns (ok, wamid_or_None, error_or_None).
def send_template_message(phone, template_name, language, body_params, button_param=None, header_image_link=None):
    components = []
    if header_image_link:
        components.append({
            "type": "header",
            "parameters": [{"type": "image", "image": {"link": header_image_link}}],
        })
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

# Fetch message templates from the WABA. Requires WHATSAPP_WABA_ID.
def list_templates():
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

# Uploads an example image via the Resumable Upload API and returns a header
# handle Meta can use when reviewing an IMAGE-header template.
# Returns (ok, handle_or_None, error_or_None).
def upload_header_image_handle(file_bytes, filename, mime_type):
    if not APP_ID:
        return False, None, "META_APP_ID is not set"
    try:
        start = requests.post(
            f"https://graph.facebook.com/{API_VERSION}/{APP_ID}/uploads",
            params={
                "file_length": len(file_bytes),
                "file_type": mime_type or "image/jpeg",
                "access_token": ACCESS_TOKEN,
            },
            timeout=30,
        )
        start_data = start.json()
        session_id = start_data.get("id")
        if not session_id:
            return False, None, f"could not start upload session: {start_data}"

        upload = requests.post(
            f"https://graph.facebook.com/{API_VERSION}/{session_id}",
            headers={
                "Authorization": f"OAuth {ACCESS_TOKEN}",
                "file_offset": "0",
            },
            data=file_bytes,
            timeout=60,
        )
        upload_data = upload.json()
        handle = upload_data.get("h")
        if not handle:
            return False, None, f"upload failed: {upload_data}"
        return True, handle, None
    except Exception as e:
        return False, None, str(e)

# Create a new template on the WABA and submit for review.
def create_template(name, language, category, body_text, button_text=None, button_url=None, header_type="NONE", header_handle=None):
    if not WABA_ID:
        return False, None, "WHATSAPP_WABA_ID is not set"
    components = []
    if header_type == "IMAGE" and header_handle:
        components.append({
            "type": "HEADER",
            "format": "IMAGE",
            "example": {"header_handle": [header_handle]},
        })
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

# end of meta_api.py
