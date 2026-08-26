"""Favorites (Recipe Save) feature — /api/favorites CRUD + re-log."""
import os
import sys
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(__file__))
from conftest import BASE_URL, client_for, insert_meal  # noqa: E402


class TestFavoritesAuth:
    def test_unauthenticated_endpoints_401(self, api_client):
        assert api_client.get(f"{BASE_URL}/api/favorites").status_code == 401
        assert api_client.post(f"{BASE_URL}/api/favorites", json={"meal_id": "x"}).status_code == 401
        assert api_client.delete(f"{BASE_URL}/api/favorites/fav_x").status_code == 401
        assert api_client.post(f"{BASE_URL}/api/favorites/fav_x/log").status_code == 401


class TestFavoritesCrud:
    def test_save_favorite_from_meal_copies_fields(self, mongo, fresh_user):
        c = client_for(fresh_user["token"])
        meal = insert_meal(mongo, fresh_user["user_id"], days_ago=0, protein=42.0, calories=555.0)
        # add a photo tag to verify exclusion
        mongo.meals.update_one({"id": meal["id"]}, {"$set": {"tags": ["photo", "breakfast"], "summary": "TEST summary"}})

        r = c.post(f"{BASE_URL}/api/favorites", json={"meal_id": meal["id"]})
        assert r.status_code == 200, r.text
        fav = r.json()
        assert fav["id"].startswith("fav_")
        assert "_id" not in fav
        assert fav["description"] == "TEST_seeded meal"
        assert fav["summary"] == "TEST summary"
        assert fav["nutrients"]["protein_g"] == 42.0
        assert fav["nutrients"]["calories"] == 555.0
        assert "photo" not in fav["tags"]
        assert "breakfast" in fav["tags"]
        assert fav["name"]  # non-empty default name

        # GET verifies persistence
        lst = c.get(f"{BASE_URL}/api/favorites")
        assert lst.status_code == 200
        ids = [f["id"] for f in lst.json()]
        assert fav["id"] in ids

    def test_save_favorite_custom_name(self, mongo, fresh_user):
        c = client_for(fresh_user["token"])
        meal = insert_meal(mongo, fresh_user["user_id"])
        r = c.post(f"{BASE_URL}/api/favorites", json={"meal_id": meal["id"], "name": "TEST_Rushed breakfast"})
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Rushed breakfast"

    def test_save_favorite_unknown_meal_404(self, fresh_user):
        c = client_for(fresh_user["token"])
        r = c.post(f"{BASE_URL}/api/favorites", json={"meal_id": "meal_does_not_exist"})
        assert r.status_code == 404

    def test_save_favorite_other_users_meal_404(self, mongo, fresh_user, session_user):
        """Ownership isolation: user A cannot favorite user B's meal."""
        other_meal = insert_meal(mongo, session_user["user_id"])
        c = client_for(fresh_user["token"])
        r = c.post(f"{BASE_URL}/api/favorites", json={"meal_id": other_meal["id"]})
        assert r.status_code == 404

    def test_save_favorite_missing_meal_id_422(self, fresh_user):
        c = client_for(fresh_user["token"])
        r = c.post(f"{BASE_URL}/api/favorites", json={})
        assert r.status_code == 422

    def test_list_newest_first(self, mongo, fresh_user):
        c = client_for(fresh_user["token"])
        m = insert_meal(mongo, fresh_user["user_id"])
        names = ["TEST_a", "TEST_b", "TEST_c"]
        created = []
        for n in names:
            r = c.post(f"{BASE_URL}/api/favorites", json={"meal_id": m["id"], "name": n})
            assert r.status_code == 200
            created.append(r.json())
        lst = c.get(f"{BASE_URL}/api/favorites").json()
        assert len(lst) == 3
        ts = [f["created_at"] for f in lst]
        assert ts == sorted(ts, reverse=True), ts
        assert lst[0]["name"] == "TEST_c"

    def test_delete_favorite_and_404_after(self, mongo, fresh_user):
        c = client_for(fresh_user["token"])
        m = insert_meal(mongo, fresh_user["user_id"])
        fav_id = c.post(f"{BASE_URL}/api/favorites", json={"meal_id": m["id"]}).json()["id"]
        d = c.delete(f"{BASE_URL}/api/favorites/{fav_id}")
        assert d.status_code == 200 and d.json().get("ok") is True
        assert fav_id not in [f["id"] for f in c.get(f"{BASE_URL}/api/favorites").json()]
        assert c.delete(f"{BASE_URL}/api/favorites/{fav_id}").status_code == 404

    def test_delete_other_users_favorite_404(self, mongo, fresh_user, session_user):
        other = client_for(session_user["token"])
        m = insert_meal(mongo, session_user["user_id"])
        fav_id = other.post(f"{BASE_URL}/api/favorites", json={"meal_id": m["id"]}).json()["id"]
        c = client_for(fresh_user["token"])
        assert c.delete(f"{BASE_URL}/api/favorites/{fav_id}").status_code == 404
        # still there for owner
        assert fav_id in [f["id"] for f in other.get(f"{BASE_URL}/api/favorites").json()]
        other.delete(f"{BASE_URL}/api/favorites/{fav_id}")


class TestFavoriteRelog:
    def test_log_favorite_creates_meal_today_and_updates_summary(self, mongo, fresh_user):
        c = client_for(fresh_user["token"])
        m = insert_meal(mongo, fresh_user["user_id"], days_ago=0, protein=30.0, calories=400.0, carbs=25.0, fat=10.0)
        fav = c.post(f"{BASE_URL}/api/favorites", json={"meal_id": m["id"], "name": "TEST_relog"}).json()

        before = c.get(f"{BASE_URL}/api/nutrition/summary").json()

        r = c.post(f"{BASE_URL}/api/favorites/{fav['id']}/log")
        assert r.status_code == 200, r.text
        meal = r.json()
        assert meal["id"].startswith("meal_")
        assert "_id" not in meal
        assert meal["source"] == "favorite"
        assert meal["from_favorite_id"] == fav["id"]
        assert "favorite" in meal["tags"]
        assert meal["nutrients"]["calories"] == 400.0
        assert meal["nutrients"]["protein_g"] == 30.0
        # created today (UTC)
        assert meal["created_at"][:10] == datetime.now(timezone.utc).date().isoformat()

        # appears in GET /api/meals
        meals = c.get(f"{BASE_URL}/api/meals").json()
        assert meal["id"] in [x["id"] for x in meals]

        after = c.get(f"{BASE_URL}/api/nutrition/summary").json()
        assert after["meal_count"] == before["meal_count"] + 1
        assert round(after["totals"]["calories"] - before["totals"]["calories"], 2) == 400.0
        assert round(after["totals"]["protein_g"] - before["totals"]["protein_g"], 2) == 30.0

    def test_repeated_log_creates_multiple_meals(self, mongo, fresh_user):
        c = client_for(fresh_user["token"])
        m = insert_meal(mongo, fresh_user["user_id"], calories=200.0, protein=10.0)
        fav = c.post(f"{BASE_URL}/api/favorites", json={"meal_id": m["id"]}).json()
        ids = set()
        for _ in range(3):
            r = c.post(f"{BASE_URL}/api/favorites/{fav['id']}/log")
            assert r.status_code == 200
            ids.add(r.json()["id"])
        assert len(ids) == 3
        assert mongo.meals.count_documents({"user_id": fresh_user["user_id"], "from_favorite_id": fav["id"]}) == 3
        summary = c.get(f"{BASE_URL}/api/nutrition/summary").json()
        assert summary["meal_count"] == 4  # seeded + 3 relogs

    def test_log_after_source_meal_deleted_still_works(self, mongo, fresh_user):
        """Favorite is a copy — deleting the origin meal must not break re-log."""
        c = client_for(fresh_user["token"])
        m = insert_meal(mongo, fresh_user["user_id"], calories=333.0)
        fav = c.post(f"{BASE_URL}/api/favorites", json={"meal_id": m["id"]}).json()
        assert c.delete(f"{BASE_URL}/api/meals/{m['id']}").status_code == 200
        r = c.post(f"{BASE_URL}/api/favorites/{fav['id']}/log")
        assert r.status_code == 200
        assert r.json()["nutrients"]["calories"] == 333.0

    def test_log_unknown_favorite_404(self, fresh_user):
        c = client_for(fresh_user["token"])
        assert c.post(f"{BASE_URL}/api/favorites/fav_nope/log").status_code == 404

    def test_log_other_users_favorite_404(self, mongo, fresh_user, session_user):
        other = client_for(session_user["token"])
        m = insert_meal(mongo, session_user["user_id"])
        fav_id = other.post(f"{BASE_URL}/api/favorites", json={"meal_id": m["id"]}).json()["id"]
        c = client_for(fresh_user["token"])
        assert c.post(f"{BASE_URL}/api/favorites/{fav_id}/log").status_code == 404
        other.delete(f"{BASE_URL}/api/favorites/{fav_id}")

    def test_relogged_meal_counts_in_streak_and_trends(self, mongo, fresh_user):
        c = client_for(fresh_user["token"])
        m = insert_meal(mongo, fresh_user["user_id"], protein=100.0, calories=500.0)
        fav = c.post(f"{BASE_URL}/api/favorites", json={"meal_id": m["id"]}).json()
        c.post(f"{BASE_URL}/api/favorites/{fav['id']}/log")
        tr = c.get(f"{BASE_URL}/api/trends/weekly")
        assert tr.status_code == 200
        today = tr.json()["days"][-1]
        assert today["protein_g"] >= 200.0
        st = c.get(f"{BASE_URL}/api/streak")
        assert st.status_code == 200
