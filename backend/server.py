"""PlateSense backend — meal nutrition analyzer with Emergent Google Auth + Claude Sonnet 5."""
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os
import uuid
import json
import re
import logging
import httpx

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="PlateSense API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("platesense")


# ---------- Models ----------
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: Optional[datetime] = None


class MealCreate(BaseModel):
    description: str


class MealPhoto(BaseModel):
    image_base64: str
    mime_type: str = "image/jpeg"
    hint: Optional[str] = None


class Nutrients(BaseModel):
    calories: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    fiber_g: float = 0
    sugar_g: float = 0
    sodium_mg: float = 0


class Goals(BaseModel):
    calories: int = 2000
    protein_g: int = 120
    carbs_g: int = 250
    fat_g: int = 65


# ---------- Auth helpers ----------
async def get_current_user(request: Request) -> User:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user_doc)


# ---------- Auth endpoints ----------
@api.post("/auth/session")
async def create_session(request: Request, response: Response):
    """Exchange Emergent session_id for our own session_token (httpOnly cookie)."""
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    async with httpx.AsyncClient(timeout=15) as hc:
        r = await hc.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session_id")
    data = r.json()

    existing = await db.users.find_one({"email": data["email"]}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": data["name"], "picture": data.get("picture")}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": data["email"],
            "name": data["name"],
            "picture": data.get("picture"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    session_token = data["session_token"]
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    })

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return {"user_id": user_id, "email": data["email"], "name": data["name"], "picture": data.get("picture")}


@api.get("/auth/me")
async def auth_me(request: Request):
    user = await get_current_user(request)
    return user.model_dump()


@api.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"ok": True}


# ---------- LLM: meal analysis ----------
MEAL_SYSTEM = """You are PlateSense, a friendly nutrition analyst. When the user describes a meal in plain language, estimate its nutrition and respond ONLY with strict JSON matching this schema:

{
  "items": [{"name": string, "quantity": string}],
  "nutrients": {
    "calories": number,
    "protein_g": number,
    "carbs_g": number,
    "fat_g": number,
    "fiber_g": number,
    "sugar_g": number,
    "sodium_mg": number
  },
  "summary": string (1-2 upbeat sentences, no emojis, ~25 words),
  "healthiness_score": integer 0-100,
  "tags": [1-4 short lowercase tags like "high-protein", "low-carb", "balanced", "sugary", "vegetarian"]
}

Rules:
- Use realistic estimates for typical portions if not specified.
- Values must be numbers, not strings.
- Do NOT wrap the JSON in markdown fences or add commentary.
- If the input is not food, return zeros and summary: "That doesn't look like food I can analyze."
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        text = m.group(0)
    return json.loads(text)


async def analyze_meal_with_ai(description: str) -> dict:
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"meal_{uuid.uuid4().hex[:10]}",
        system_message=MEAL_SYSTEM,
    ).with_model("anthropic", "claude-sonnet-5")
    resp = await chat.send_message(UserMessage(text=description))
    return _extract_json(resp)


PHOTO_SYSTEM = MEAL_SYSTEM + """

You are analyzing a PHOTO of a meal. First identify the visible dishes and portions, then estimate nutrition. Include a short "description" field (max 12 words) naming what you see, in place of user text. Return only the JSON object described above, plus a top-level "description" string field.
"""


async def analyze_photo_with_ai(image_b64: str, mime_type: str, hint: Optional[str]) -> dict:
    prompt = "Analyze this meal photo and return the JSON."
    if hint:
        prompt += f" User hint: {hint}"
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"photo_{uuid.uuid4().hex[:10]}",
        system_message=PHOTO_SYSTEM,
    ).with_model("gemini", "gemini-2.5-flash-image")
    resp = await chat.send_message(UserMessage(
        text=prompt,
        file_contents=[ImageContent(image_base64=image_b64)],
    ))
    return _extract_json(resp)


# ---------- Meals ----------
@api.post("/meals")
async def create_meal(payload: MealCreate, request: Request):
    user = await get_current_user(request)
    if not payload.description.strip():
        raise HTTPException(status_code=400, detail="description required")

    try:
        parsed = await analyze_meal_with_ai(payload.description)
    except Exception as e:
        log.exception("AI analysis failed")
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {e}")

    nutrients = Nutrients(**parsed.get("nutrients", {})).model_dump()
    meal_id = f"meal_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    doc = {
        "id": meal_id,
        "user_id": user.user_id,
        "description": payload.description.strip(),
        "items": parsed.get("items", []),
        "nutrients": nutrients,
        "summary": parsed.get("summary", ""),
        "healthiness_score": int(parsed.get("healthiness_score", 0)),
        "tags": parsed.get("tags", []),
        "created_at": now.isoformat(),
    }
    await db.meals.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/meals")
async def list_meals(request: Request, limit: int = 100):
    user = await get_current_user(request)
    cursor = db.meals.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


@api.delete("/meals/{meal_id}")
async def delete_meal(meal_id: str, request: Request):
    user = await get_current_user(request)
    result = await db.meals.delete_one({"id": meal_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Meal not found")
    return {"ok": True}


# ---------- Favorites (saved recipes) ----------
class FavoriteFromMeal(BaseModel):
    meal_id: str
    name: Optional[str] = None


@api.post("/favorites")
async def save_favorite(payload: FavoriteFromMeal, request: Request):
    user = await get_current_user(request)
    meal = await db.meals.find_one({"id": payload.meal_id, "user_id": user.user_id}, {"_id": 0})
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    fav_id = f"fav_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    doc = {
        "id": fav_id,
        "user_id": user.user_id,
        "source_meal_id": payload.meal_id,
        "name": (payload.name or meal.get("description", "Saved meal")).strip()[:80],
        "description": meal.get("description", ""),
        "items": meal.get("items", []),
        "nutrients": meal.get("nutrients", {}),
        "summary": meal.get("summary", ""),
        "healthiness_score": meal.get("healthiness_score", 0),
        "tags": [t for t in meal.get("tags", []) if t != "photo"],
        "created_at": now.isoformat(),
    }
    await db.favorites.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/favorites")
async def list_favorites(request: Request):
    user = await get_current_user(request)
    cursor = db.favorites.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).limit(200)
    return await cursor.to_list(length=200)


@api.delete("/favorites/{fav_id}")
async def delete_favorite(fav_id: str, request: Request):
    user = await get_current_user(request)
    result = await db.favorites.delete_one({"id": fav_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"ok": True}


@api.post("/favorites/{fav_id}/log")
async def log_favorite(fav_id: str, request: Request):
    """Re-log a saved favorite as a new meal today — no AI call, instant."""
    user = await get_current_user(request)
    fav = await db.favorites.find_one({"id": fav_id, "user_id": user.user_id}, {"_id": 0})
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    meal_id = f"meal_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    doc = {
        "id": meal_id,
        "user_id": user.user_id,
        "description": fav.get("description") or fav.get("name", ""),
        "items": fav.get("items", []),
        "nutrients": fav.get("nutrients", {}),
        "summary": fav.get("summary", ""),
        "healthiness_score": fav.get("healthiness_score", 0),
        "tags": (fav.get("tags", []) or []) + ["favorite"],
        "source": "favorite",
        "from_favorite_id": fav_id,
        "created_at": now.isoformat(),
    }
    await db.meals.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.post("/meals/photo")
async def create_meal_from_photo(payload: MealPhoto, request: Request):
    user = await get_current_user(request)
    if not payload.image_base64.strip():
        raise HTTPException(status_code=400, detail="image_base64 required")

    # strip data URL prefix if present
    b64 = payload.image_base64
    if b64.startswith("data:"):
        b64 = b64.split(",", 1)[-1]

    mt = (payload.mime_type or "").lower()
    if mt not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="mime_type must be image/jpeg, image/png, or image/webp")
    # rough size cap ~8MB after base64 (~10MB encoded)
    if len(b64) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="image too large (max ~8MB)")

    try:
        parsed = await analyze_photo_with_ai(b64, payload.mime_type, payload.hint)
    except Exception as e:
        log.exception("photo AI failed")
        raise HTTPException(status_code=502, detail=f"AI photo analysis failed: {e}")

    nutrients = Nutrients(**parsed.get("nutrients", {})).model_dump()
    description = (parsed.get("description") or payload.hint or "Meal photo").strip()
    meal_id = f"meal_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    doc = {
        "id": meal_id,
        "user_id": user.user_id,
        "description": description,
        "items": parsed.get("items", []),
        "nutrients": nutrients,
        "summary": parsed.get("summary", ""),
        "healthiness_score": int(parsed.get("healthiness_score", 0)),
        "tags": parsed.get("tags", []) + ["photo"],
        "source": "photo",
        "created_at": now.isoformat(),
    }
    await db.meals.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ---------- Goals ----------
@api.get("/goals")
async def get_goals(request: Request):
    user = await get_current_user(request)
    doc = await db.goals.find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return Goals().model_dump()
    return {k: doc[k] for k in ("calories", "protein_g", "carbs_g", "fat_g") if k in doc}


@api.put("/goals")
async def update_goals(goals: Goals, request: Request):
    user = await get_current_user(request)
    payload = goals.model_dump()
    payload["user_id"] = user.user_id
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.goals.update_one({"user_id": user.user_id}, {"$set": payload}, upsert=True)
    return goals.model_dump()


# ---------- Daily summary ----------
async def _summary_for(user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    cursor = db.meals.find(
        {"user_id": user_id, "created_at": {"$gte": day_start.isoformat()}},
        {"_id": 0},
    )
    meals = await cursor.to_list(length=500)
    totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0, "sugar_g": 0.0, "sodium_mg": 0.0}
    for m in meals:
        n = m.get("nutrients", {})
        for k in totals:
            totals[k] += float(n.get(k, 0) or 0)
    goals_doc = await db.goals.find_one({"user_id": user_id}, {"_id": 0}) or Goals().model_dump()
    goals = {k: goals_doc.get(k, Goals().model_dump()[k]) for k in ("calories", "protein_g", "carbs_g", "fat_g")}
    remaining = {
        "calories": max(0, goals["calories"] - totals["calories"]),
        "protein_g": max(0, goals["protein_g"] - totals["protein_g"]),
        "carbs_g": max(0, goals["carbs_g"] - totals["carbs_g"]),
        "fat_g": max(0, goals["fat_g"] - totals["fat_g"]),
    }
    return {"date": day_start.date().isoformat(), "totals": totals, "goals": goals, "remaining": remaining, "meal_count": len(meals)}


@api.get("/nutrition/summary")
async def nutrition_summary(request: Request):
    user = await get_current_user(request)
    return await _summary_for(user.user_id)


# ---------- Weekly trends ----------
@api.get("/trends/weekly")
async def weekly_trends(request: Request):
    user = await get_current_user(request)
    now = datetime.now(timezone.utc)
    today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start = today - timedelta(days=6)
    cursor = db.meals.find(
        {"user_id": user.user_id, "created_at": {"$gte": start.isoformat()}},
        {"_id": 0, "created_at": 1, "nutrients": 1},
    )
    meals = await cursor.to_list(length=2000)

    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        days.append({
            "date": d.date().isoformat(),
            "label": d.strftime("%a"),
            "calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0,
        })
    idx_by_date = {d["date"]: d for d in days}

    for m in meals:
        try:
            d = datetime.fromisoformat(m["created_at"]).astimezone(timezone.utc).date().isoformat()
        except Exception:
            continue
        bucket = idx_by_date.get(d)
        if not bucket:
            continue
        n = m.get("nutrients", {})
        bucket["calories"] += float(n.get("calories", 0) or 0)
        bucket["protein_g"] += float(n.get("protein_g", 0) or 0)
        bucket["carbs_g"] += float(n.get("carbs_g", 0) or 0)
        bucket["fat_g"] += float(n.get("fat_g", 0) or 0)

    goals_doc = await db.goals.find_one({"user_id": user.user_id}, {"_id": 0}) or Goals().model_dump()
    goals = {k: goals_doc.get(k, Goals().model_dump()[k]) for k in ("calories", "protein_g", "carbs_g", "fat_g")}
    return {"days": days, "goals": goals}


# ---------- Streak (protein goal streak) ----------
@api.get("/streak")
async def protein_streak(request: Request):
    user = await get_current_user(request)
    goals_doc = await db.goals.find_one({"user_id": user.user_id}, {"_id": 0}) or Goals().model_dump()
    protein_goal = float(goals_doc.get("protein_g", Goals().protein_g))

    now = datetime.now(timezone.utc)
    today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    lookback = today - timedelta(days=30)

    cursor = db.meals.find(
        {"user_id": user.user_id, "created_at": {"$gte": lookback.isoformat()}},
        {"_id": 0, "created_at": 1, "nutrients": 1},
    )
    meals = await cursor.to_list(length=5000)

    per_day = {}
    for m in meals:
        try:
            d = datetime.fromisoformat(m["created_at"]).astimezone(timezone.utc).date().isoformat()
        except Exception:
            continue
        per_day[d] = per_day.get(d, 0.0) + float(m.get("nutrients", {}).get("protein_g", 0) or 0)

    streak = 0
    # start from today; if today not hit yet, look from yesterday (grace)
    todays_protein = per_day.get(today.date().isoformat(), 0.0)
    start_offset = 0 if todays_protein >= protein_goal else 1
    for i in range(start_offset, 30):
        day_key = (today - timedelta(days=i)).date().isoformat()
        if per_day.get(day_key, 0.0) >= protein_goal:
            streak += 1
        else:
            break

    hit_today = todays_protein >= protein_goal
    return {
        "streak": streak,
        "hit_today": hit_today,
        "todays_protein": todays_protein,
        "protein_goal": protein_goal,
        "milestone": streak >= 3 and hit_today,
    }


# ---------- AI suggestions ----------
SUGGEST_SYSTEM = """You are a friendly nutritionist. Given a user's remaining daily nutrition budget, suggest 3 realistic meals or snacks that fit. Respond ONLY with strict JSON:

{
  "suggestions": [
    {"title": string, "why": string (one short sentence, upbeat), "approx_calories": number, "approx_protein_g": number}
  ]
}
No markdown fences, no extra prose."""


@api.post("/suggestions")
async def suggestions(request: Request):
    user = await get_current_user(request)
    summary = await _summary_for(user.user_id)
    remaining = summary["remaining"]
    prompt = (
        f"Remaining today: {int(remaining['calories'])} kcal, "
        f"{int(remaining['protein_g'])}g protein, "
        f"{int(remaining['carbs_g'])}g carbs, "
        f"{int(remaining['fat_g'])}g fat. "
        "Suggest 3 meals/snacks the user could eat next."
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"suggest_{uuid.uuid4().hex[:10]}",
            system_message=SUGGEST_SYSTEM,
        ).with_model("anthropic", "claude-sonnet-5")
        resp = await chat.send_message(UserMessage(text=prompt))
        data = _extract_json(resp)
    except Exception as e:
        log.exception("suggestion ai failed")
        raise HTTPException(status_code=502, detail=f"AI suggestion failed: {e}")
    return data


@api.get("/")
async def root():
    return {"ok": True, "app": "PlateSense"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def _shutdown():
    client.close()
