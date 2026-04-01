# Render Deployment Guide — Planitt

This guide focuses on deploying the **NestJS backend** (MongoDB + public read APIs) while ensuring the **AI stack (Ollama + FastAPI signal processor)** stays private and is never publicly reachable.

## 1) Deploy MongoDB Atlas
1. Create a MongoDB Atlas cluster.
2. Create a database user with read/write permissions for the `planitt` database.
3. Get your connection string (e.g. `mongodb+srv://planitt:123@planitt.mongodb.net/`).

## 2) Deploy `planitt-backend` on Render (public)
Create a **Web Service** for the NestJS backend.

### Required environment variables
- `NODE_ENV=production`
- `PORT=3000`
- `MONGODB_URI=<your-atlas-connection-string>`
- `JWT_SECRET=<generate-a-strong-secret>`
- `PLANITT_INTERNAL_API_KEY=<shared-internal-api-key>`

## 2.1) Deploy `planitt-admin` on Netlify (public, Option A)
The admin app does not call Render directly from the browser. It uses server-side Next.js route handlers, so Netlify environment variables must be configured correctly.

### Required Netlify environment variables
- `NEST_API_BASE_URL=https://planitt-backend-crypto.onrender.com`
- `NEST_API_INTERNAL_API_KEY=<same-as-PLANITT_INTERNAL_API_KEY>`
- `ADMIN_DEPLOYMENT_MODE=public_nest_only`
- `FASTAPI_BASE_URL=https://127.0.0.1.invalid` (placeholder, unused in Option A)
- `FASTAPI_INTERNAL_API_KEY=<optional in Option A>`
- `NEXTAUTH_SECRET=<strong-random-secret>`
- `ADMIN_USERNAME=<admin-user>`
- `ADMIN_PASSWORD=<admin-password>`

If `NEST_API_INTERNAL_API_KEY` is omitted, admin routes fall back to JWT mode and require `NEST_API_JWT`.

### CORS
Backend CORS is configured via `CORS_ORIGINS` (comma-separated). In production, set this explicitly (for example your Netlify domain and local admin origin).

## 3) Run FastAPI signal-processing locally (private, Option A)
The FastAPI service is the **signal-processing engine** and stays local/private. It is only meant to call the backend internal endpoint.

### Required environment variables
- `ENABLE_POSTGRES_DB_INIT=false`
- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://ollama:11434` (when using Docker networking)
- `OLLAMA_MODEL=mistral` (or your chosen model)
- `PLANITT_BACKEND_BASE_URL=<your-backend-origin>` (example: `https://planitt-backend-crypto.onrender.com`)
- `PLANITT_BACKEND_INTERNAL_API_KEY=<same-as-planitt-backend>`
- `PLANITT_PROCESSOR_INTERNAL_API_KEY=<any-internal-key>`
- `PLANITT_MIN_CONFIDENCE=70`

### Keep Ollama and processor private (important)
Do not expose Ollama or FastAPI with any public port mapping.

## 4) Internal API call flow (Option A)
1. FastAPI processor posts to the backend internal endpoint:
   - `POST /signals`
   - Header: `x-api-key: <PLANITT_INTERNAL_API_KEY>`
2. Backend stores the structured signal in MongoDB.
3. Clients fetch public signals with:
   - `GET /signals` and `GET /signals/:id`
   - Header: `Authorization: Bearer <JWT>`
4. Admin/public clients read only from Nest; FastAPI-backed operator endpoints are disabled in Netlify `public_nest_only` mode.

Note on naming:
- `NEST_API_BASE_URL`: used by Netlify admin server routes.
- `PLANITT_BACKEND_BASE_URL`: used by FastAPI processor when forwarding to Nest backend.

## 5) Notes / gaps
- This repo scaffolds JWT validation but does not include login/signup endpoints for generating JWTs.
  - You can integrate your existing auth system, or add a simple `/auth/login` later.
- “Hit TP/Hit SL” status transitions require execution/price monitoring logic not included yet.

