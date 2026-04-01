# Render Deployment Guide — Planitt

This guide focuses on deploying the **NestJS backend** (MongoDB + public read APIs) while ensuring the **AI stack (Ollama + FastAPI signal processor)** stays private and is never publicly reachable.

## 1) Deploy MongoDB Atlas
1. Create a MongoDB Atlas cluster.
2. Create a database user with read/write permissions for the `planitt` database.
3. Get your connection string (e.g. `mongodb+srv://planittcrypto_db_user:XD0ITbU8bHCdhaE1@planitt.5hxwdty.mongodb.net/`).

## 2) Deploy `planitt-backend` on Render (public)
Create a **Web Service** for the NestJS backend.

### Required environment variables
- `NODE_ENV=production`
- `PORT=3000`
- `MONGODB_URI=<your-atlas-connection-string>`
- `JWT_SECRET=<generate-a-strong-secret>`
- `PLANITT_INTERNAL_API_KEY=<shared-internal-api-key>`

### CORS
The backend enables CORS permissively via `app.enableCors({ origin: true, credentials: true })`.
If you need to restrict origins, update `main.ts` to use a concrete whitelist.

## 3) Deploy FastAPI signal-processing on Render (private)
The FastAPI service is the **signal-processing engine** and is only meant to call the backend internal endpoint.

### Required environment variables
- `ENABLE_POSTGRES_DB_INIT=false`
- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://ollama:11434` (when using Docker networking)
- `OLLAMA_MODEL=mistral` (or your chosen model)
- `PLANITT_BACKEND_BASE_URL=<your-backend-origin>` (example: `https://<your-backend>.onrender.com`)
- `PLANITT_BACKEND_INTERNAL_API_KEY=<same-as-planitt-backend>`
- `PLANITT_PROCESSOR_INTERNAL_API_KEY=<any-internal-key>`
- `PLANITT_MIN_CONFIDENCE=70`

### Keep Ollama private (important)
Do not expose Ollama with a public port mapping.
Recommended approach:
- Run `ollama` and `signal-processing` in the same private Docker network (e.g. a Render private service + Docker, or a single container/microservice bundle).
- Ensure the Docker configuration exposes Ollama only internally (use `expose`, not `ports`).

In `docker-compose.planitt.yml`, this is already modeled as:
- Ollama has `expose: 11434` and **no** `ports` mapping.
- `signal-processing` points to Ollama via `http://ollama:11434`.

## 4) Internal API call flow
1. FastAPI processor posts to the backend internal endpoint:
   - `POST /signals`
   - Header: `x-api-key: <PLANITT_INTERNAL_API_KEY>`
2. Backend stores the structured signal in MongoDB.
3. Clients fetch public signals with:
   - `GET /signals` and `GET /signals/:id`
   - Header: `Authorization: Bearer <JWT>`

## 5) Notes / gaps
- This repo scaffolds JWT validation but does not include login/signup endpoints for generating JWTs.
  - You can integrate your existing auth system, or add a simple `/auth/login` later.
- “Hit TP/Hit SL” status transitions require execution/price monitoring logic not included yet.

