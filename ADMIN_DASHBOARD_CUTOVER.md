# Planitt Admin Dashboard Cutover Guide

This guide migrates from the legacy static dashboard at `static/index.html` to the new Next.js admin app at `apps/planitt-admin`.

## 1) Keep old dashboard intact during validation
- Keep FastAPI static mount behavior unchanged.
- Run Next.js admin in parallel on a separate host/subdomain first (for example `admin.planitt.yourdomain.com`).

## 2) Configure new admin app
In `apps/planitt-admin/.env.local`:

- `NEXTAUTH_SECRET`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `NEST_API_BASE_URL`
- `NEST_API_JWT`
- `FASTAPI_BASE_URL`
- `FASTAPI_INTERNAL_API_KEY`

## 3) Validate functional parity
Checklist:
- Login works and `/dashboard/*` is protected.
- Signals list reads from NestJS (`GET /signals`) with pagination and filters.
- Manual generation triggers FastAPI via server-side proxy.
- News and market status are visible via FastAPI internal endpoints.
- Ops health page shows Nest/FastAPI service availability.

## 4) Traffic switch options
Choose one:

1. **Subdomain strategy (recommended):**
   - Keep root app unchanged.
   - Publish Next.js as `admin.*`.
   - Announce new admin URL to operators.

2. **Root replacement strategy:**
   - Replace legacy static root route with redirect to Next.js admin host.
   - Keep static file as fallback artifact.

## 5) Rollback plan
- If admin issues occur, route operators back to the legacy static dashboard URL immediately.
- Keep both deployments available until 1-2 weeks of stable operations.

## 6) Security checks before cutover
- Confirm no internal keys are exposed in browser network logs.
- Confirm FastAPI internal routes reject requests without `x-api-key`.
- Confirm NestJS public reads require valid JWT.
- Rotate internal keys once production is stable.

