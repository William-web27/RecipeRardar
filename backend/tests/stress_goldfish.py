# One-off intermittency probe for the 'goldfish' 404 bug (not part of the pytest suite).
# Usage: python /app/backend/tests/stress_goldfish.py
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
be = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or fe["REACT_APP_BACKEND_URL"]).rstrip("/")
db = MongoClient(be["MONGO_URL"])[be["DB_NAME"]]

uid = f"TEST_stress_{uuid.uuid4().hex[:8]}"
token = f"TEST_stress_tok_{uuid.uuid4().hex[:12]}"
db.users.insert_one({"user_id": uid, "email": f"{uid}@example.com", "name": "Stress",
                     "picture": "https://via.placeholder.com/150",
                     "created_at": datetime.now(timezone.utc).isoformat()})
db.user_sessions.insert_one({"user_id": uid, "session_token": token,
                             "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
                             "created_at": datetime.now(timezone.utc)})

H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def call(i):
    try:
        r = requests.post(f"{BASE_URL}/api/meals", json={"description": "goldfish"}, headers=H, timeout=120)
        body = r.text[:200] if r.status_code != 200 else ""
        return i, r.status_code, body
    except Exception as e:  # noqa: BLE001
        return i, "EXC", str(e)[:200]


try:
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(call, range(12)))
    codes = {}
    for i, code, body in results:
        codes[code] = codes.get(code, 0) + 1
        if code != 200:
            print(f"  call {i}: {code} {body}")
    print("STATUS DISTRIBUTION:", codes)
    print("ANY 404:", 404 in codes)
    sys.exit(0 if codes.get(200, 0) == len(results) else 1)
finally:
    db.meals.delete_many({"user_id": uid})
    db.user_sessions.delete_many({"user_id": uid})
    db.users.delete_many({"user_id": uid})
