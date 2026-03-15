# CampusIQ

CampusIQ is a monorepo for an AI-assisted academic platform. V1 focuses on clean project structure for role-based experiences across students, teachers, and admins, without implementing business logic yet.

## Project Overview

- Teachers will upload study documents and later generate AI summaries and quizzes.
- Students will study with summaries, flashcards, and quizzes.
- Admins will manage platform access and inspect high-level activity.
- The current state is scaffold-only: routes, folders, environment shape, and starter UI/API entry points.

## Tech Stack

- Frontend: React 19, Vite, Tailwind CSS, React Router
- Backend: FastAPI, Pydantic Settings, SQLAlchemy
- Infra: Redis
- Planned integrations: Supabase, Anthropic

## Folder Structure

```text
campusiq/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── router.py
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tasks/
│   │   ├── utils/
│   │   └── main.py
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── store/
│   │   └── utils/
│   └── .env.example
└── .env.example
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server will start on the Vite default port, usually `http://localhost:5173`.

## Run Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Backend API will start on `http://localhost:8000`, with health available at `http://localhost:8000/health`.

## Required Environment Variables

You can keep a shared root `.env` or separate frontend/backend env files.

### Shared / Backend

- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ANTHROPIC_API_KEY`
- `REDIS_URL`
- `JWT_SECRET_KEY`

### Frontend

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_BASE_URL`

## Current Scaffold Notes

- Backend routers are mounted under `/api/v1`.
- Each backend route module includes a placeholder endpoint only.
- No authentication, database models, or business workflows are implemented yet.
- Frontend routes and pages are placeholders with Tailwind-based layout and navigation.
