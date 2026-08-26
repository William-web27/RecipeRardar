# Tests for the "goldfish 404" bug fix: AI retry helper + normalized 502 error path
import os
import sys
import asyncio

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import BASE_URL  # noqa: E402

GOLDFISH_INPUTS = ["goldfish", "goldfish crackers", "a handful of goldfish crackers"]
OTHER_INPUTS = ["an apple", "cup of black coffee"]


def _post_meal(client, description, timeout=90):
    return client.post(f"{BASE_URL}/api/meals", json={"description": description}, timeout=timeout)


def _assert_meal_shape(data, description):
    assert isinstance(data.get("id"), str), f"missing id: {data}"
    assert data["id"].startswith("meal_"), f"bad id prefix: {data['id']}"
    assert data["description"] == description
    n = data.get("nutrients")
    assert isinstance(n, dict), f"nutrients missing: {data}"
    for k in ("calories", "protein_g", "carbs_g", "fat_g"):
        assert k in n, f"nutrient {k} missing: {n}"
        assert isinstance(n[k], (int, float)) and not isinstance(n[k], bool), f"{k} not numeric: {n[k]!r}"
    assert isinstance(data.get("summary"), str) and data["summary"].strip(), f"empty summary: {data}"
    assert isinstance(data.get("tags"), list)
    assert isinstance(data.get("healthiness_score"), int)
    assert "_id" not in data


# ---------- REPRO: the reported 'goldfish' 404 ----------
class TestGoldfishRepro:
    @pytest.mark.parametrize("description", GOLDFISH_INPUTS)
    def test_goldfish_variants_return_200(self, auth_client, description):
        r = _post_meal(auth_client, description)
        assert r.status_code != 404, f"REGRESSION: 404 leaked for '{description}': {r.text[:400]}"
        assert r.status_code == 200, f"status {r.status_code} for '{description}': {r.text[:400]}"
        data = r.json()
        _assert_meal_shape(data, description)

    def test_goldfish_repeated_three_times(self, auth_client):
        """Same exact input the user reported, 3x in a row, to catch intermittency."""
        statuses = []
        for _ in range(3):
            r = _post_meal(auth_client, "goldfish")
            statuses.append(r.status_code)
            if r.status_code == 200:
                _assert_meal_shape(r.json(), "goldfish")
            elif r.status_code == 502:
                assert "briefly unavailable" in r.json().get("detail", "")
        assert 404 not in statuses, f"404 observed in repeated goldfish calls: {statuses}"
        assert all(s in (200, 502) for s in statuses), statuses
        assert statuses.count(200) >= 1, f"no successful goldfish analysis: {statuses}"

    def test_meal_persisted_and_retrievable(self, auth_client):
        r = _post_meal(auth_client, "goldfish crackers")
        assert r.status_code == 200, r.text[:300]
        meal_id = r.json()["id"]
        g = auth_client.get(f"{BASE_URL}/api/meals", timeout=30)
        assert g.status_code == 200
        ids = [m["id"] for m in g.json()]
        assert meal_id in ids, "created goldfish meal not persisted in GET /api/meals"


# ---------- Error path must be 502, never 404 ----------
class TestAIErrorNormalization:
    def test_retry_helper_retries_and_raises_last(self):
        """Unit-level: _retry_ai makes 2 attempts and recovers on 2nd success."""
        from server import _retry_ai

        calls = {"n": 0}

        async def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("upstream 404")
            return {"ok": True}

        out = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_retry_ai(flaky, delay=0.01))
        assert out == {"ok": True}
        assert calls["n"] == 2, "retry did not happen"

    def test_retry_helper_raises_after_all_tries(self):
        from server import _retry_ai

        calls = {"n": 0}

        async def always_fail():
            calls["n"] += 1
            raise RuntimeError("boom")

        loop = asyncio.get_event_loop_policy().new_event_loop()
        with pytest.raises(RuntimeError):
            loop.run_until_complete(_retry_ai(always_fail, delay=0.01))
        assert calls["n"] == 2

    def test_endpoints_map_ai_failure_to_502(self):
        """Static guarantee: all AI endpoints raise 502 (not 404) on terminal AI failure."""
        src = open("/app/backend/server.py", encoding="utf-8").read()
        assert src.count("status_code=502") >= 3, "expected 3 AI endpoints raising 502"
        assert "briefly unavailable" in src
        # AI failure handlers must not raise 404
        for marker in ("AI analysis failed", "Photo analysis"):
            assert marker in src

    def test_empty_description_is_400_not_404(self, auth_client):
        r = auth_client.post(f"{BASE_URL}/api/meals", json={"description": "   "}, timeout=30)
        assert r.status_code == 400, r.text[:300]
        assert "required" in r.json()["detail"].lower()

    def test_unauthenticated_is_401_not_404(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/meals", json={"description": "goldfish"}, timeout=30)
        assert r.status_code == 401, r.text[:300]

    def test_unknown_meal_delete_404_shape(self, auth_client):
        """The only legitimate 404 on /api/meals/* is DELETE of a non-existent meal."""
        r = auth_client.delete(f"{BASE_URL}/api/meals/does-not-exist", timeout=30)
        assert r.status_code == 404
        assert r.json()["detail"] == "Meal not found"

    def test_no_get_single_meal_route(self, auth_client):
        """Documented: GET /api/meals/{id} does not exist (405) — no 404 confusion source."""
        r = auth_client.get(f"{BASE_URL}/api/meals/does-not-exist", timeout=30)
        assert r.status_code == 405


# ---------- Regression: other short inputs ----------
class TestShortInputRegression:
    @pytest.mark.parametrize("description", OTHER_INPUTS)
    def test_other_short_items(self, auth_client, description):
        r = _post_meal(auth_client, description)
        assert r.status_code == 200, f"status {r.status_code} for '{description}': {r.text[:400]}"
        _assert_meal_shape(r.json(), description)

    def test_non_food_input_still_200(self, auth_client):
        r = _post_meal(auth_client, "a plastic chair")
        assert r.status_code in (200,), f"{r.status_code}: {r.text[:300]}"
        assert isinstance(r.json()["nutrients"]["calories"], (int, float))


# ---------- Regression: read endpoints + suggestions + favorites flow ----------
class TestEndpointRegression:
    @pytest.mark.parametrize("path", [
        "/api/meals",
        "/api/nutrition/summary",
        "/api/streak",
        "/api/trends/weekly",
        "/api/goals",
        "/api/favorites",
    ])
    def test_get_endpoints_200(self, auth_client, path):
        r = auth_client.get(f"{BASE_URL}{path}", timeout=45)
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:300]}"

    def test_suggestions_200(self, auth_client):
        r = auth_client.post(f"{BASE_URL}/api/suggestions", timeout=90)
        assert r.status_code != 404, f"404 leaked from suggestions: {r.text[:300]}"
        assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
        data = r.json()
        assert isinstance(data.get("suggestions"), list), data

    def test_favorites_flow(self, auth_client):
        m = _post_meal(auth_client, "an apple")
        assert m.status_code == 200, m.text[:300]
        meal_id = m.json()["id"]

        f = auth_client.post(f"{BASE_URL}/api/favorites", json={"meal_id": meal_id}, timeout=30)
        assert f.status_code == 200, f.text[:300]
        fav_id = f.json()["id"]

        lst = auth_client.get(f"{BASE_URL}/api/favorites", timeout=30)
        assert lst.status_code == 200
        assert fav_id in [x["id"] for x in lst.json()]

        logged = auth_client.post(f"{BASE_URL}/api/favorites/{fav_id}/log", timeout=30)
        assert logged.status_code == 200, logged.text[:300]
        new_meal = logged.json()
        assert new_meal["id"].startswith("meal_") and new_meal["id"] != meal_id
        assert isinstance(new_meal["nutrients"]["calories"], (int, float))

        d = auth_client.delete(f"{BASE_URL}/api/favorites/{fav_id}", timeout=30)
        assert d.status_code == 200
