"""Tiny Supabase REST client used by all services (service-role, backend only)."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend import config

REST = f"{config.SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": config.SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
}

_session = requests.Session()
_retry = Retry(total=4, connect=4, read=4, backoff_factor=1.0,
               status_forcelist=[429, 500, 502, 503, 504], allowed_methods=None)
_session.mount("https://", HTTPAdapter(max_retries=_retry))


def query(table, params=None, limit=None):
    params = dict(params or {})
    params["select"] = params.get("select", "*")
    if limit:
        params["limit"] = limit
    r = _session.get(f"{REST}/{table}", headers=HEADERS, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def count(table, params=None):
    r = _session.head(f"{REST}/{table}", headers={**HEADERS, "Prefer": "count=exact"},
                      params={"select": "id", **(params or {})}, timeout=60)
    r.raise_for_status()
    return int(r.headers.get("content-range", "*/0").split("/")[-1])
