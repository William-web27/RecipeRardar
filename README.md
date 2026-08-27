# RecipeRadar

RecipeRadar is a meal nutrition tracker that turns plain-English meal descriptions into structured nutrition data. Users can sign in with Google, save analyzed meals, track daily calories and macros, set nutrition goals, and request AI meal suggestions.

## Features

- Analyze meals from natural-language descriptions
- Track calories, protein, carbohydrates, fat, fiber, sugar, and sodium
- View meal history and daily nutrition summaries
- Set daily calorie and macro goals
- Get AI-generated meal suggestions
- Authenticate with Emergent Google OAuth

## Stack

- Frontend: React 19, React Router, Tailwind CSS, shadcn/ui, Recharts, Framer Motion
- Backend: FastAPI, Motor, MongoDB
- AI: Claude Sonnet through `emergentintegrations`
- Authentication: Emergent Google OAuth with an httpOnly session cookie

## Project Layout

```text
backend/       FastAPI application and Python tests
frontend/      React application
memory/        Product requirements and project notes
test_reports/  Test reports from previous iterations
```

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- Yarn 1.x or npm
- A running MongoDB instance
- An Emergent LLM key and OAuth configuration

## Configuration

Create `backend/.env`:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=reciperadar
EMERGENT_LLM_KEY=your-emergent-llm-key
```

Create `frontend/.env`:

```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

Do not commit either `.env` file or real credentials.

## Run Locally

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`, with interactive documentation at `http://localhost:8000/docs`.

### Frontend

In a second terminal:

```powershell
cd frontend
yarn install
yarn start
```

Open `http://localhost:3000` in a browser.

## Tests

Run the backend test suite from the repository root:

```powershell
cd backend
pytest
```

Run frontend tests in interactive mode:

```powershell
cd frontend
yarn test
```

Create a production frontend build with:

```powershell
cd frontend
yarn build
```

## API Overview

All application endpoints are prefixed with `/api`.

| Area | Endpoints |
| --- | --- |
| Authentication | `GET /auth/me`, `POST /auth/session`, `POST /auth/logout` |
| Meals | `POST /meals`, `GET /meals`, `DELETE /meals/{id}` |
| Goals | `GET /goals`, `PUT /goals` |
| Nutrition | `GET /nutrition/summary` |
| Suggestions | `POST /suggestions` |

Authenticated requests use the session cookie or an `Authorization: Bearer <token>` header.
