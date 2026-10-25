import os
from fastapi import Request
from fastapi.responses import RedirectResponse

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "changeme")


def is_logged_in(request: Request) -> bool:
    return bool(request.session.get("logged_in"))


def require_login(request: Request):
    """Use as a dependency-like guard inside route handlers:
    if (resp := require_login(request)): return resp
    """
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=302)
    return None
