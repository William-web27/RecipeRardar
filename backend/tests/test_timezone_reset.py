"""Iteration 6 — daily reset at LOCAL midnight via ?tz_offset= (JS getTimezoneOffset semantics).

Covers: /api/nutrition/summary, /api/streak, /api/trends/weekly, /api/suggestions.
tz_offset = minutes to ADD to local time to get UTC (EDT=240, IST=-330).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from conftest import BASE_URL, client_for


def _expected_local_date(tz_offset: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=tz_offset)).date().isoformat()


def _local_day_start_utc(tz_offset: int) -> datetime:
    now = datetime.now(timezone.utc)
    local_now = now - timedelta(minutes=tz_offset)
    midnight = datetime(local_now.year, local_now.month, local_now.day, tzinfo=timezone.utc)
    return midnight + timedelta(minutes=tz_offset)


def _insert_meal_at(db, user_id, created_at_utc: datetime, protein=130.0, calories=600.0):
    doc = {
        "id": f"meal_TEST_{uuid.uuid4().hex[:10]}",
        "user_id": user_id,
        "description": "TEST_tz meal",
        "items": [],
        "nutrients": {
            "calories": calories, "protein_g": protein, "carbs_g": 50.0,
            "fat_g": 20.0, "fiber_g": 5.0, "sugar_g": 4.0, "sodium_mg": 300.0,
        },
        "summary": "TEST tz seeded",
        "healthiness_score": 70,
        "tags": ["test"],
        "created_at": created_at_utc.isoformat(),
    }
    db.meals.insert_one(doc)
    return doc


# ---------- feature: /api/nutrition/summary?tz_offset= ----------
class TestSummaryTzDate:
    @pytest.mark.parametrize("tz", [0, 240, -330, 60, -720])
    def test_summary_date_matches_local_date(self, fresh_user, tz):
        c = client_for(fresh_user["token"])
        r = c.get(f"{BASE_URL}/api/nutrition/summary", params={"tz_offset": tz})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["date"] == _expected_local_date(tz), (tz, d["date"])
        assert isinstance(d["meal_count"], int)
        assert set(d["totals"].keys()) >= {"calories", "protein_g", "carbs_g", "fat_g"}

    def test_default_tz_offset_equals_utc(self, fresh_user):
        c = client_for(fresh_user["token"])
        no_param = c.get(f"{BASE_URL}/api/nutrition/summary").json()
        explicit = c.get(f"{BASE_URL}/api/nutrition/summary", params={"tz_offset": 0}).json()
        assert no_param["date"] == explicit["date"] == datetime.now(timezone.utc).date().isoformat()
        assert no_param["meal_count"] == explicit["meal_count"]

    def test_meal_before_local_midnight_excluded(self, mongo, fresh_user):
        """A meal 30 min before the EDT local midnight must not count toward EDT 'today'."""
        c = client_for(fresh_user["token"])
        tz = 240
        _insert_meal_at(mongo, fresh_user["user_id"], _local_day_start_utc(tz) - timedelta(minutes=30))
        _insert_meal_at(mongo, fresh_user["user_id"], datetime.now(timezone.utc) - timedelta(minutes=1))
        d = c.get(f"{BASE_URL}/api/nutrition/summary", params={"tz_offset": tz}).json()
        assert d["meal_count"] == 1, d
        assert d["totals"]["calories"] == 600.0

    def test_invalid_tz_offset_type_422(self, fresh_user):
        c = client_for(fresh_user["token"])
        r = c.get(f"{BASE_URL}/api/nutrition/summary", params={"tz_offset": "abc"})
        assert r.status_code == 422, r.text

    def test_extreme_tz_offset_clamped(self, fresh_user):
        c = client_for(fresh_user["token"])
        # Out-of-range tz_offset now returns 422 (validated by FastAPI Query(ge=-840, le=840))
        r = c.get(f"{BASE_URL}/api/nutrition/summary", params={"tz_offset": 100000})
        assert r.status_code == 422, r.text
        r = c.get(f"{BASE_URL}/api/nutrition/summary", params={"tz_offset": -100000})
        assert r.status_code == 422, r.text

    def test_unauthenticated_401(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/nutrition/summary", params={"tz_offset": 240},
                           headers={"Authorization": ""})
        assert r.status_code == 401


# ---------- feature: /api/trends/weekly?tz_offset= ----------
class TestTrendsTz:
    @pytest.mark.parametrize("tz", [0, 240, -330])
    def test_last_bucket_is_local_today(self, fresh_user, tz):
        c = client_for(fresh_user["token"])
        r = c.get(f"{BASE_URL}/api/trends/weekly", params={"tz_offset": tz})
        assert r.status_code == 200, r.text
        days = r.json()["days"]
        assert len(days) == 7
        assert days[-1]["date"] == _expected_local_date(tz)
        dates = [d["date"] for d in days]
        assert dates == sorted(dates)

    def test_boundary_meal_buckets_into_local_yesterday(self, mongo, fresh_user):
        """Meal 30 min before EDT midnight -> bucket = local yesterday for tz=240,
        and = its UTC date for tz=0."""
        tz = 240
        c = client_for(fresh_user["token"])
        created = _local_day_start_utc(tz) - timedelta(minutes=30)
        _insert_meal_at(mongo, fresh_user["user_id"], created, calories=777.0)

        local_expected = (created - timedelta(minutes=tz)).date().isoformat()
        days = c.get(f"{BASE_URL}/api/trends/weekly", params={"tz_offset": tz}).json()["days"]
        bucket = {d["date"]: d for d in days}
        assert bucket[local_expected]["calories"] == 777.0, days
        assert bucket[_expected_local_date(tz)]["calories"] == 0.0 or local_expected == _expected_local_date(tz)

        utc_expected = created.date().isoformat()
        days0 = c.get(f"{BASE_URL}/api/trends/weekly", params={"tz_offset": 0}).json()["days"]
        b0 = {d["date"]: d for d in days0}
        assert b0[utc_expected]["calories"] == 777.0, days0

    def test_three_meals_near_boundary_bucket_correctly(self, mongo, fresh_user):
        tz = 240
        c = client_for(fresh_user["token"])
        start = _local_day_start_utc(tz)
        stamps = [start - timedelta(hours=2), start - timedelta(minutes=1), start + timedelta(minutes=1)]
        for s in stamps:
            _insert_meal_at(mongo, fresh_user["user_id"], s, calories=100.0)
        days = c.get(f"{BASE_URL}/api/trends/weekly", params={"tz_offset": tz}).json()["days"]
        bucket = {d["date"]: d["calories"] for d in days}
        yday = (start - timedelta(minutes=tz) - timedelta(days=1)).date().isoformat()
        today = _expected_local_date(tz)
        assert bucket.get(yday) == 200.0, (bucket, yday)
        assert bucket.get(today) == 100.0, (bucket, today)


# ---------- feature: /api/streak?tz_offset= ----------
class TestStreakTz:
    def test_streak_uses_local_days(self, mongo, fresh_user):
        tz = 240
        c = client_for(fresh_user["token"])
        assert c.put(f"{BASE_URL}/api/goals", json={
            "calories": 2000, "protein_g": 100, "carbs_g": 250, "fat_g": 65}).status_code == 200
        start = _local_day_start_utc(tz)
        _insert_meal_at(mongo, fresh_user["user_id"], start - timedelta(minutes=30), protein=130.0)
        _insert_meal_at(mongo, fresh_user["user_id"], datetime.now(timezone.utc) - timedelta(minutes=1), protein=130.0)
        d = c.get(f"{BASE_URL}/api/streak", params={"tz_offset": tz}).json()
        assert d["hit_today"] is True, d
        assert d["todays_protein"] == 130.0, d
        assert d["streak"] == 2, d

    def test_streak_today_zero_when_meal_belongs_to_local_yesterday(self, mongo, fresh_user):
        tz = 240
        c = client_for(fresh_user["token"])
        c.put(f"{BASE_URL}/api/goals", json={"calories": 2000, "protein_g": 100, "carbs_g": 250, "fat_g": 65})
        _insert_meal_at(mongo, fresh_user["user_id"],
                        _local_day_start_utc(tz) - timedelta(minutes=30), protein=130.0)
        d = c.get(f"{BASE_URL}/api/streak", params={"tz_offset": tz}).json()
        assert d["hit_today"] is False, d
        assert d["todays_protein"] == 0.0, d
        assert d["streak"] == 1, d
        assert d["milestone"] is False

    @pytest.mark.parametrize("tz", [0, -330])
    def test_streak_shape_with_tz(self, fresh_user, tz):
        c = client_for(fresh_user["token"])
        r = c.get(f"{BASE_URL}/api/streak", params={"tz_offset": tz})
        assert r.status_code == 200
        d = r.json()
        assert d["streak"] == 0 and d["hit_today"] is False and d["todays_protein"] == 0.0


# ---------- feature: /api/suggestions?tz_offset= ----------
class TestSuggestionsTz:
    def test_suggestions_accepts_tz_offset(self, auth_client):
        r = auth_client.post(f"{BASE_URL}/api/suggestions", params={"tz_offset": -330}, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("suggestions"), list) and len(d["suggestions"]) >= 1
        assert "title" in d["suggestions"][0]
