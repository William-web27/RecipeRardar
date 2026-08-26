"""PlateSense backend tests — iteration 2 (streak, weekly trends, photo meals + regression)."""
import base64
import os
from datetime import datetime, timedelta, timezone

import pytest

from conftest import BASE_URL, client_for, insert_meal

IMAGE_PATH = "/tmp/lunch.jpg"


# ---------- module: health / auth ----------
class TestHealthAuth:
    def test_root(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/")
        assert r.status_code == 200
        assert r.json() == {"ok": True, "app": "PlateSense"}

    def test_me_unauthenticated(self, api_client):
        s = api_client
        r = s.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": ""})
        assert r.status_code == 401

    def test_me_authenticated(self, auth_client, session_user):
        r = auth_client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        d = r.json()
        assert d["user_id"] == session_user["user_id"]
        assert d["email"].startswith("TEST_")
        assert d["name"] == "QA Tester"

    def test_streak_unauthenticated(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/streak", headers={"Authorization": ""})
        assert r.status_code == 401

    def test_trends_unauthenticated(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/trends/weekly", headers={"Authorization": ""})
        assert r.status_code == 401


# ---------- feature: GET /api/streak ----------
class TestStreak:
    def test_streak_zero_with_no_meals(self, fresh_user):
        c = client_for(fresh_user["token"])
        r = c.get(f"{BASE_URL}/api/streak")
        assert r.status_code == 200
        d = r.json()
        assert d["streak"] == 0
        assert d["hit_today"] is False
        assert d["todays_protein"] == 0
        assert d["protein_goal"] == 120
        assert d["milestone"] is False

    def test_streak_four_days_with_milestone(self, mongo, fresh_user):
        for days_ago in (0, 1, 2, 3):
            insert_meal(mongo, fresh_user["user_id"], days_ago=days_ago, protein=130.0)
        c = client_for(fresh_user["token"])
        r = c.get(f"{BASE_URL}/api/streak")
        assert r.status_code == 200
        d = r.json()
        assert d["streak"] == 4, d
        assert d["hit_today"] is True
        assert d["todays_protein"] == 130.0
        assert d["milestone"] is True

    def test_streak_breaks_on_missed_day(self, mongo, fresh_user):
        # today + yesterday hit, day 2 missing, day 3 hit -> streak should be 2
        insert_meal(mongo, fresh_user["user_id"], days_ago=0, protein=130.0)
        insert_meal(mongo, fresh_user["user_id"], days_ago=1, protein=130.0)
        insert_meal(mongo, fresh_user["user_id"], days_ago=3, protein=130.0)
        c = client_for(fresh_user["token"])
        d = c.get(f"{BASE_URL}/api/streak").json()
        assert d["streak"] == 2, d
        assert d["milestone"] is False

    def test_streak_respects_custom_goal(self, mongo, fresh_user):
        c = client_for(fresh_user["token"])
        assert c.put(f"{BASE_URL}/api/goals", json={
            "calories": 2000, "protein_g": 200, "carbs_g": 250, "fat_g": 65}).status_code == 200
        insert_meal(mongo, fresh_user["user_id"], days_ago=0, protein=130.0)
        d = c.get(f"{BASE_URL}/api/streak").json()
        assert d["protein_goal"] == 200
        assert d["hit_today"] is False
        assert d["streak"] == 0


# ---------- feature: GET /api/trends/weekly ----------
class TestWeeklyTrends:
    def test_shape_and_chronological_order(self, fresh_user):
        c = client_for(fresh_user["token"])
        r = c.get(f"{BASE_URL}/api/trends/weekly")
        assert r.status_code == 200
        d = r.json()
        assert set(d.keys()) == {"days", "goals"}
        assert len(d["days"]) == 7
        dates = [x["date"] for x in d["days"]]
        assert dates == sorted(dates)
        today = datetime.now(timezone.utc).date().isoformat()
        assert dates[-1] == today
        expected_first = (datetime.now(timezone.utc).date() - timedelta(days=6)).isoformat()
        assert dates[0] == expected_first
        for day in d["days"]:
            for k in ("date", "label", "calories", "protein_g", "carbs_g", "fat_g"):
                assert k in day
            assert isinstance(day["label"], str) and len(day["label"]) == 3
        assert d["goals"] == {"calories": 2000, "protein_g": 120, "carbs_g": 250, "fat_g": 65}

    def test_meal_reflected_in_correct_day_bucket(self, mongo, fresh_user):
        insert_meal(mongo, fresh_user["user_id"], days_ago=2, protein=45.0, calories=700.0)
        insert_meal(mongo, fresh_user["user_id"], days_ago=2, protein=15.0, calories=300.0)
        target = (datetime.now(timezone.utc).date() - timedelta(days=2)).isoformat()
        c = client_for(fresh_user["token"])
        days = c.get(f"{BASE_URL}/api/trends/weekly").json()["days"]
        bucket = next(x for x in days if x["date"] == target)
        assert bucket["calories"] == 1000.0
        assert bucket["protein_g"] == 60.0
        others = [x for x in days if x["date"] != target]
        assert all(x["calories"] == 0 for x in others)

    def test_meals_outside_window_excluded(self, mongo, fresh_user):
        insert_meal(mongo, fresh_user["user_id"], days_ago=10, protein=99.0, calories=999.0)
        c = client_for(fresh_user["token"])
        days = c.get(f"{BASE_URL}/api/trends/weekly").json()["days"]
        assert sum(x["calories"] for x in days) == 0


# ---------- feature: POST /api/meals/photo ----------
class TestPhotoMeal:
    def test_empty_image_returns_400(self, auth_client):
        r = auth_client.post(f"{BASE_URL}/api/meals/photo", json={"image_base64": "   ", "mime_type": "image/jpeg"})
        assert r.status_code == 400
        assert "image_base64" in r.json()["detail"]

    def test_unauthenticated_returns_401(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/meals/photo",
                            json={"image_base64": "abc", "mime_type": "image/jpeg"},
                            headers={"Authorization": ""})
        assert r.status_code == 401

    def test_photo_meal_contract(self, auth_client, mongo, session_user):
        assert os.path.exists(IMAGE_PATH), "test image missing"
        b64 = base64.b64encode(open(IMAGE_PATH, "rb").read()).decode()
        payload = {"image_base64": b64, "mime_type": "image/jpeg", "hint": "plate of food"}
        r = auth_client.post(f"{BASE_URL}/api/meals/photo", json=payload, timeout=120)
        if r.status_code == 502:
            # retry once per instructions
            r = auth_client.post(f"{BASE_URL}/api/meals/photo", json=payload, timeout=120)
        assert r.status_code == 200, f"{r.status_code}: {r.text[:600]}"
        d = r.json()
        assert "_id" not in d
        assert d["id"].startswith("meal_")
        assert d["source"] == "photo"
        assert "photo" in d["tags"]
        assert isinstance(d["description"], str) and d["description"]
        for k in ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg"):
            assert isinstance(d["nutrients"][k], (int, float))
        assert isinstance(d["healthiness_score"], int)
        assert isinstance(d["summary"], str)
        # persistence
        got = auth_client.get(f"{BASE_URL}/api/meals").json()
        assert any(m["id"] == d["id"] and m.get("source") == "photo" for m in got)


# ---------- regression: goals, text meals, summary, suggestions ----------
class TestRegression:
    def test_goals_put_get(self, fresh_user):
        c = client_for(fresh_user["token"])
        assert c.get(f"{BASE_URL}/api/goals").json() == {
            "calories": 2000, "protein_g": 120, "carbs_g": 250, "fat_g": 65}
        payload = {"calories": 2200, "protein_g": 140, "carbs_g": 260, "fat_g": 70}
        r = c.put(f"{BASE_URL}/api/goals", json=payload)
        assert r.status_code == 200
        assert r.json() == payload
        assert c.get(f"{BASE_URL}/api/goals").json() == payload

    def test_text_meal_crud_and_summary(self, fresh_user):
        c = client_for(fresh_user["token"])
        r = c.post(f"{BASE_URL}/api/meals", json={"description": "2 scrambled eggs and whole wheat toast"}, timeout=120)
        assert r.status_code == 200, r.text[:500]
        meal = r.json()
        assert meal["id"].startswith("meal_")
        assert meal["nutrients"]["calories"] > 0
        assert meal["nutrients"]["protein_g"] > 0
        assert isinstance(meal["tags"], list)
        assert "_id" not in meal

        listed = c.get(f"{BASE_URL}/api/meals").json()
        assert any(m["id"] == meal["id"] for m in listed)

        summary = c.get(f"{BASE_URL}/api/nutrition/summary").json()
        assert summary["meal_count"] == 1
        assert summary["totals"]["calories"] == meal["nutrients"]["calories"]
        assert summary["remaining"]["calories"] == max(0, 2000 - meal["nutrients"]["calories"])

        # trends today bucket reflects the meal
        days = c.get(f"{BASE_URL}/api/trends/weekly").json()["days"]
        assert days[-1]["calories"] == meal["nutrients"]["calories"]

        d = c.delete(f"{BASE_URL}/api/meals/{meal['id']}")
        assert d.status_code == 200 and d.json() == {"ok": True}
        assert all(m["id"] != meal["id"] for m in c.get(f"{BASE_URL}/api/meals").json())

    def test_text_meal_empty_description_400(self, auth_client):
        r = auth_client.post(f"{BASE_URL}/api/meals", json={"description": "  "})
        assert r.status_code == 400

    def test_delete_missing_meal_404(self, auth_client):
        r = auth_client.delete(f"{BASE_URL}/api/meals/meal_does_not_exist")
        assert r.status_code == 404

    def test_suggestions(self, auth_client):
        r = auth_client.post(f"{BASE_URL}/api/suggestions", timeout=120)
        assert r.status_code == 200, r.text[:500]
        s = r.json()["suggestions"]
        assert len(s) == 3
        for item in s:
            assert item["title"]
            assert item["why"]
            assert isinstance(item["approx_calories"], (int, float))
            assert isinstance(item["approx_protein_g"], (int, float))
