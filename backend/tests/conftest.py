import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")

base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")


@pytest.fixture(scope="session")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


def _make_user(db):
    uid = f"TEST_user_{uuid.uuid4().hex[:10]}"
    token = f"TEST_session_{uuid.uuid4().hex[:16]}"
    db.users.insert_one({
        "user_id": uid,
        "email": f"TEST_{uid}@example.com",
        "name": "QA Tester",
        "picture": "https://via.placeholder.com/150",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    db.user_sessions.insert_one({
        "user_id": uid,
        "session_token": token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc),
    })
    return uid, token


def _cleanup_user(db, uid):
    db.meals.delete_many({"user_id": uid})
    db.goals.delete_many({"user_id": uid})
    db.user_sessions.delete_many({"user_id": uid})
    db.users.delete_many({"user_id": uid})


@pytest.fixture(scope="session")
def session_user(mongo):
    """Primary auth'd test user for the whole session."""
    uid, token = _make_user(mongo)
    yield {"user_id": uid, "token": token}
    _cleanup_user(mongo, uid)


@pytest.fixture
def fresh_user(mongo):
    """Isolated user per test (for streak/trends math)."""
    uid, token = _make_user(mongo)
    yield {"user_id": uid, "token": token}
    _cleanup_user(mongo, uid)


@pytest.fixture(scope="session")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_client(session_user):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {session_user['token']}",
    })
    return s


def client_for(token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return s


def insert_meal(db, user_id, days_ago=0, protein=130.0, calories=600.0, carbs=50.0, fat=20.0):
    now = datetime.now(timezone.utc)
    day = datetime(now.year, now.month, now.day, 12, 0, tzinfo=timezone.utc) - timedelta(days=days_ago)
    doc = {
        "id": f"meal_TEST_{uuid.uuid4().hex[:10]}",
        "user_id": user_id,
        "description": "TEST_seeded meal",
        "items": [],
        "nutrients": {
            "calories": calories, "protein_g": protein, "carbs_g": carbs,
            "fat_g": fat, "fiber_g": 5.0, "sugar_g": 4.0, "sodium_mg": 300.0,
        },
        "summary": "TEST seeded",
        "healthiness_score": 70,
        "tags": ["test"],
        "created_at": day.isoformat(),
    }
    db.meals.insert_one(doc)
    return doc
