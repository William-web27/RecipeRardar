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

from emergentintegrations.llm.chat import LlmChat, UserMessage

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
