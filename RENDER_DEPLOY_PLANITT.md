# Render Deployment Guide — Planitt

This guide focuses on deploying only the **NestJS backend** (MongoDB + signal carrier APIs) while keeping the **AI stack (Ollama + FastAPI signal processor)** local/private.

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
- `CORS_ORIGINS=<comma-separated web/app origins>`

## 2.1) Deploy `planitt-admin` on Netlify (public, hybrid mode)
The admin app does not call Render directly from the browser. It uses server-side Next.js route handlers, so Netlify environment variables must be configured correctly.

### Required Netlify environment variables
- `NEST_API_BASE_URL=https://planitt-backend-crypto.onrender.com`
- `NEST_API_INTERNAL_API_KEY=<same-as-PLANITT_INTERNAL_API_KEY>`
- `ADMIN_DEPLOYMENT_MODE=hybrid`
- `FASTAPI_BASE_URL=<private-fastapi-ops-url>`
- `FASTAPI_INTERNAL_API_KEY=<same-as-PLANITT_PROCESSOR_INTERNAL_API_KEY>`
- `NEXTAUTH_SECRET=<strong-random-secret>`
- `ADMIN_USERNAME=<admin-user>`
- `ADMIN_PASSWORD=<admin-password>`

If `NEST_API_INTERNAL_API_KEY` is omitted, admin routes fall back to JWT mode and require `NEST_API_JWT`.

### CORS
Backend CORS is configured via `CORS_ORIGINS` (comma-separated). In production, set this explicitly (for example your Netlify domain and local admin origin).

## 3) FastAPI runtime: local scanner only
Use FastAPI only as a local/private signal producer. Do not run FastAPI as a public Render service.

### Local scanner required environment variables
- `ENABLE_POSTGRES_DB_INIT=false`
- `ENABLE_BACKGROUND_SCANNER=true`
- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://ollama:11434` (when using Docker networking)
- `OLLAMA_MODEL=mistral` (or your chosen model)
- `PLANITT_BACKEND_BASE_URL=<your-backend-origin>`
- `PLANITT_BACKEND_INTERNAL_API_KEY=<same-as-planitt-backend>`
- `PLANITT_PROCESSOR_INTERNAL_API_KEY=<any-internal-key>`
- `PLANITT_MIN_CONFIDENCE=70`

### Keep strategy internals private (important)
Do not expose local scanner/Ollama publicly. Keep generation local or in a private network only.

## 4) Internal API call flow (hybrid)
1. FastAPI processor posts to the backend internal endpoint:
   - `POST /signals`
   - Header: `x-api-key: <PLANITT_INTERNAL_API_KEY>`
2. Backend stores the structured signal in MongoDB.
3. Web/app fetches signals with:
   - `GET /signals` and `GET /signals/:id`
   - Header: `x-api-key: <PLANITT_INTERNAL_API_KEY>`
4. Optional admin tools can use `GET /internal/*` endpoints with the same API key.

Note on naming:
- `NEST_API_BASE_URL`: used by Netlify admin server routes.
- `PLANITT_BACKEND_BASE_URL`: used by FastAPI processor when forwarding to Nest backend.

## 5) Notes / gaps
- Keep `JWT_SECRET` set even if current reads use API key mode, so future auth extensions remain safe.
- “Hit TP/Hit SL” status transitions require execution/price monitoring logic not included yet.

