# PlateSense — Product Requirements

## Original Problem Statement
"i want to build an app that basically i would say my meal and it would tell about the meal like how much protein and all the other things."

## User Choices (Feb 2026)
- Input: text description only
- AI: Claude Sonnet 5 (primary) via Emergent LLM Key
- Auth: Emergent Google Auth + meal history stored server-side
- Features: daily nutrition summary/tracking, daily calorie/protein goals, AI meal suggestions
- Vibe: readable, clear, playful but on-theme (Fredoka + Nunito, tangerine + mint)

## Personas
- Health-curious eater who wants a quick, judgment-free way to log meals in plain English and see macros/progress.

## Architecture
- Backend: FastAPI, MongoDB (motor), emergentintegrations (LlmChat, Claude Sonnet 5)
- Frontend: React 19, react-router-dom v7, Tailwind + shadcn/ui, framer-motion, recharts, sonner
- Auth: Emergent Google OAuth; session_token in httpOnly cookie + Bearer fallback

## Endpoints
- GET /api/auth/me | POST /api/auth/session | POST /api/auth/logout
- POST /api/meals (analyze + save) | GET /api/meals | DELETE /api/meals/{id}
- GET /api/goals | PUT /api/goals
- GET /api/nutrition/summary
- POST /api/suggestions

## Implemented (Feb 2026)
- Full auth flow, meal analysis w/ Claude Sonnet 5 (structured JSON macros)
- Dashboard with rings, meal history, goal setting, AI suggestions
- Playful landing page with Fredoka/Nunito, tangerine + mint palette

## Backlog
- P1: photo/image meal input (Gemini Nano Banana)
- P1: weekly/monthly trend charts
- P2: shareable meal cards, streaks/gamification
- P2: barcode scanner, restaurant menu import
