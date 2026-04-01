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

## 3) FastAPI split: local scanner + hosted private ops
Use two runtimes for FastAPI code:
- **Local Docker scanner runtime**: generates and forwards signals automatically.
- **Hosted private ops runtime**: serves admin operations endpoints (`/health`, `/api/v1/news`, `/api/v1/signals/*`) with scanner disabled.

### Local scanner required environment variables
- `ENABLE_POSTGRES_DB_INIT=false`
- `ENABLE_BACKGROUND_SCANNER=true`
- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://ollama:11434` (when using Docker networking)
- `OLLAMA_MODEL=mistral` (or your chosen model)
- `PLANITT_BACKEND_BASE_URL=<your-backend-origin>` (example: `https://planitt-backend-crypto.onrender.com`)
- `PLANITT_BACKEND_INTERNAL_API_KEY=<same-as-planitt-backend>`
- `PLANITT_PROCESSOR_INTERNAL_API_KEY=<any-internal-key>`
- `PLANITT_MIN_CONFIDENCE=70`

### Hosted private ops required environment variables
- `ENABLE_POSTGRES_DB_INIT=false`
- `ENABLE_BACKGROUND_SCANNER=false`
- `FASTAPI_CORS_ORIGINS=https://planitt-crypto.netlify.app`
- `FASTAPI_TRUSTED_HOSTS=<private-fastapi-hostname>`
- `PLANITT_BACKEND_BASE_URL=https://planitt-backend-crypto.onrender.com`
- `PLANITT_BACKEND_INTERNAL_API_KEY=<same-as-planitt-backend>`
- `PLANITT_PROCESSOR_INTERNAL_API_KEY=<same-as-netlify-fastapi-internal-key>`

### Keep strategy internals private (important)
Do not expose local scanner/Ollama publicly. Hosted FastAPI ops should be ingress-restricted and protected by `x-api-key`.

## 4) Internal API call flow (hybrid)
1. FastAPI processor posts to the backend internal endpoint:
   - `POST /signals`
   - Header: `x-api-key: <PLANITT_INTERNAL_API_KEY>`
2. Backend stores the structured signal in MongoDB.
3. Clients fetch public signals with:
   - `GET /signals` and `GET /signals/:id`
   - Header: `Authorization: Bearer <JWT>`
4. Hosted admin calls Nest for signals/performance and private FastAPI for news/market-status/generate.

Note on naming:
- `NEST_API_BASE_URL`: used by Netlify admin server routes.
- `PLANITT_BACKEND_BASE_URL`: used by FastAPI processor when forwarding to Nest backend.

## 5) Notes / gaps
- This repo scaffolds JWT validation but does not include login/signup endpoints for generating JWTs.
  - You can integrate your existing auth system, or add a simple `/auth/login` later.
- “Hit TP/Hit SL” status transitions require execution/price monitoring logic not included yet.

