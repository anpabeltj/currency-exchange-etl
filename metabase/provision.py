"""
Provision Metabase from code.

1. Wait until Metabase is up
2. Create the admin user on first start (or log in if it already exists)
3. Add the currency PostgreSQL database
4. Create every card from dashboard.json and the SQL files in queries/
5. Create the dashboard (or reuse an empty one) and place the cards on it

Safe to run many times. If the dashboard already has cards, it stops.
If an earlier run failed and left an empty dashboard, it fills that one.
Uses only the Python standard library so the container needs no pip install.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent
MB_URL = os.environ.get("MB_URL", "http://metabase:3000").rstrip("/")
DATABASE_NAME = "Currency DB"
STARTUP_TIMEOUT_SECONDS = 900


def log(message):
    print(f"[metabase-setup] {message}", flush=True)


def api_request(method, path, payload=None, session_id=None):
    headers = {"Content-Type": "application/json"}
    if session_id:
        headers["X-Metabase-Session"] = session_id

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(MB_URL + path, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed with HTTP {error.code}: {detail}") from error

    if not body:
        return None
    return json.loads(body)


def wait_for_metabase():
    log(f"Waiting for Metabase at {MB_URL}")
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS

    while time.time() < deadline:
        try:
            health = api_request("GET", "/api/health")
            if health and health.get("status") == "ok":
                log("Metabase is ready")
                return
        except (urllib.error.URLError, ConnectionError, RuntimeError, TimeoutError):
            pass
        time.sleep(5)

    raise RuntimeError("Metabase did not become healthy in time")


def get_session():
    email = os.environ["MB_ADMIN_EMAIL"]
    password = os.environ["MB_ADMIN_PASSWORD"]

    properties = api_request("GET", "/api/session/properties")

    if not properties.get("has-user-setup"):
        log("First start, creating admin user")
        payload = {
            "token": properties["setup-token"],
            "user": {
                "first_name": "Admin",
                "last_name": "User",
                "email": email,
                "password": password,
                "site_name": "Currency Exchange",
            },
            "prefs": {
                "site_name": "Currency Exchange",
                "site_locale": "en",
                "allow_tracking": False,
            },
        }
        result = api_request("POST", "/api/setup", payload)
        return result["id"]

    log("Admin already exists, logging in")
    result = api_request("POST", "/api/session", {"username": email, "password": password})
    return result["id"]


def as_list(response):
    """Some Metabase endpoints return a list, others wrap it in {"data": [...]}."""
    if isinstance(response, dict):
        return response.get("data", [])
    return response


def find_dashboard(session_id, name):
    response = api_request("GET", "/api/search?models=dashboard&q=" + urllib.request.quote(name), session_id=session_id)
    for item in as_list(response):
        if item.get("name") == name and not item.get("archived"):
            return item["id"]
    return None


def get_or_create_database(session_id):
    databases = as_list(api_request("GET", "/api/database", session_id=session_id))
    for database in databases:
        if database.get("name") == DATABASE_NAME:
            log(f"Database '{DATABASE_NAME}' already exists (id {database['id']})")
            return database["id"]

    payload = {
        "engine": "postgres",
        "name": DATABASE_NAME,
        "details": {
            "host": os.environ["DB_HOST"],
            "port": int(os.environ.get("DB_PORT", "5432")),
            "dbname": os.environ["DB_NAME"],
            "user": os.environ["DB_USER"],
            "password": os.environ["DB_PASS"],
            "ssl": False,
        },
    }
    database = api_request("POST", "/api/database", payload, session_id)
    log(f"Created database '{DATABASE_NAME}' (id {database['id']})")
    return database["id"]


def create_card(session_id, database_id, card_definition):
    query_path = BASE_DIR / "queries" / card_definition["query_file"]
    sql = query_path.read_text()

    payload = {
        "name": card_definition["name"],
        "type": "question",
        "display": card_definition["display"],
        "visualization_settings": card_definition["visualization_settings"],
        "dataset_query": {
            "type": "native",
            "database": database_id,
            "native": {"query": sql, "template-tags": {}},
        },
    }
    card = api_request("POST", "/api/card", payload, session_id)
    log(f"Created card '{card_definition['name']}' (id {card['id']})")
    return card["id"]


def check_query_files(definition):
    """Fail before touching Metabase if any SQL file is missing."""
    missing = []
    for card_definition in definition["cards"]:
        query_path = BASE_DIR / "queries" / card_definition["query_file"]
        if not query_path.exists():
            missing.append(card_definition["query_file"])

    if missing:
        raise RuntimeError(f"Missing SQL files in metabase/queries: {', '.join(missing)}")


def fill_dashboard(session_id, database_id, dashboard_id, definition):
    """Create every card and place it on an existing dashboard."""
    dashcards = []
    temporary_id = -1
    for card_definition in definition["cards"]:
        card_id = create_card(session_id, database_id, card_definition)
        layout = card_definition["layout"]
        dashcards.append(
            {
                "id": temporary_id,
                "card_id": card_id,
                "row": layout["row"],
                "col": layout["col"],
                "size_x": layout["size_x"],
                "size_y": layout["size_y"],
                "parameter_mappings": [],
                "visualization_settings": {},
            }
        )
        temporary_id = temporary_id - 1

    api_request(
        "PUT",
        f"/api/dashboard/{dashboard_id}",
        {"dashcards": dashcards, "width": "full"},
        session_id,
    )
    log(f"Placed {len(dashcards)} cards on the dashboard")

def archive_dashboard(session_id, dashboard):
    """Move a dashboard and its cards to the Metabase trash."""
    for dashcard in dashboard.get("dashcards", []):
        card_id = dashcard.get("card_id")
        if card_id:
            api_request("PUT", f"/api/card/{card_id}", {"archived": True}, session_id)
    api_request("PUT", f"/api/dashboard/{dashboard['id']}", {"archived": True}, session_id)
    log(f"Archived dashboard {dashboard['id']} and its cards")

def main():
    definition = json.loads((BASE_DIR / "dashboard.json").read_text())
    check_query_files(definition)
    recreate = os.environ.get("MB_RECREATE_DASHBOARD", "false").lower() == "true"

    wait_for_metabase()
    session_id = get_session()
    database_id = get_or_create_database(session_id)

    dashboard_id = find_dashboard(session_id, definition["name"])

    if dashboard_id:
        dashboard = api_request("GET", f"/api/dashboard/{dashboard_id}", session_id=session_id)
        if dashboard.get("dashcards") and recreate:
            archive_dashboard(session_id, dashboard)
            dashboard_id = None
        elif dashboard.get("dashcards"):
            log(f"Dashboard already has cards at http://localhost:3000/dashboard/{dashboard_id}, nothing to do")
            log("Run with MB_RECREATE_DASHBOARD=true to rebuild it from dashboard.json")
            return
        else:
            log(f"Dashboard {dashboard_id} exists but is empty, filling it")

    if not dashboard_id:
        dashboard = api_request(
            "POST",
            "/api/dashboard",
            {"name": definition["name"], "description": definition["description"]},
            session_id,
        )
        dashboard_id = dashboard["id"]
        log(f"Created dashboard '{definition['name']}' (id {dashboard_id})")

    fill_dashboard(session_id, database_id, dashboard_id, definition)
    log(f"Done. Open http://localhost:3000/dashboard/{dashboard_id}")

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        log(f"FAILED: {error}")
        sys.exit(1)
